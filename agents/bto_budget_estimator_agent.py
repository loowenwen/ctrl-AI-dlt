import boto3
import json
import logging
import os
from botocore.config import Config

from strands import Agent, tool
from strands.handlers.callback_handler import PrintingCallbackHandler
from strands.models.bedrock import BedrockModel

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# standard annuity formula to compute maximum loan given monthly repayment
def max_hdb_loan(pmt_monthly, annual_rate=0.03, years=25):
    r = annual_rate / 12.0
    N = years * 12
    factor = (1 + r) ** N
    L = pmt_monthly * (factor - 1) / (r * factor)
    return round(L, 2)

# estimate maximum HDB loan given monthly household income, tenure, and rate
@tool
def estimate_hdb_loan(household_income: int, annual_rate: float = 0.03, years: int = 25) -> float:
    """
    Estimate the max HDB loan based on household income.
    - household_income: combined monthly income
    - annual_rate: annual interest rate (default 3%)
    - years: loan tenure in years (default 25)
    """
    pmt_monthly = 0.30 * household_income
    r = annual_rate / 12.0
    N = years * 12
    factor = (1 + r) ** N
    L = pmt_monthly * (factor - 1) / (r * factor)
    return round(L, 2)

WS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-west-2")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "openai.gpt-oss-120b-1:0")

session = boto3.Session()

model = BedrockModel(
    model_id=BEDROCK_MODEL_ID,
    max_tokens=1024,
    boto_client_config=Config(
        read_timeout=120,
        connect_timeout=120,
        retries=dict(max_attempts=3, mode="adaptive"),
    ),
    boto_session=session
)

SYSTEM_PROMPT = """
You are a Singapore HDB loan affordability assistant.

You can:
- Calculate the maximum HDB loan based on user inputs
- Use 30% of combined household income as the max repayment
- Assume 25 years tenure (unless specified)
- Use stress interest rate = max(HDB concessionary 2.6%, 3.0%)
- Explain results clearly and simply

When users ask:
- Extract their income, tenure, and rate if provided
- Call the loan calculator tool to get the result
- Present the answer in easy-to-understand terms
""".strip()

loan_agent = Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=[estimate_hdb_loan],
    callback_handler=PrintingCallbackHandler()
)

def main():
    prompts = [
        "My household income is 9000, can you estimate my HDB loan?",
        "We earn 7000 a month combined, want 20 years tenure, how much can we borrow?",
        "If we earn 12000, what's the max HDB loan with 25 years tenure?"
    ]
    for prompt in prompts:
        print(f"**Prompt**: {prompt}")
        response = loan_agent(prompt)
        print("\n" + "-" * 80 + "\n")


if __name__ == "__main__":
    main()