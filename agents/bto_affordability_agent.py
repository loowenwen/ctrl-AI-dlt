import os
import logging
from dotenv import load_dotenv
from botocore.config import Config
import boto3
from strands import Agent, tool
from strands.handlers.callback_handler import PrintingCallbackHandler
from strands.models.bedrock import BedrockModel

# -------------------------------
# load environment variables
# -------------------------------
load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN")  

AWS_REGION = "us-east-1"
BEDROCK_MODEL_ID = "arn:aws:bedrock:us-east-1:371061166839:inference-profile/us.anthropic.claude-3-5-sonnet-20241022-v2:0"


# -------------------------------
# logging setup
# -------------------------------
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# -------------------------------
# financial calculation helpers
# -------------------------------
def max_hdb_loan_from_income(income, annual_rate=0.03, years=25):
    """compute max HDB loan based on monthly household income"""
    monthly_payment = 0.3 * income  # 30% of household income
    r = annual_rate / 12.0
    N = years * 12
    factor = (1 + r)**N
    loan = monthly_payment * (factor - 1) / (r * factor)
    return round(loan, 2)

def total_hdb_budget(cash_savings, cpf_savings, max_loan):
    """total available budget including cash + CPF + loan"""
    return round(cash_savings + cpf_savings + max_loan, 2)

# -------------------------------
# strands tool: hdb loan + budget
# -------------------------------
@tool
def estimate_hdb_loan_with_budget(
    household_income: int,
    cash_savings: float,
    cpf_savings: float,
    bto_price: float,
    annual_rate: float = 0.03,
    tenure_years: int = 25
):
    """
    estimate hdb loan and total budget including cash + cpf
    
    returns max loan, total budget, and affordability status
    """
    max_loan = max_hdb_loan_from_income(household_income, annual_rate, tenure_years)
    total_budget = total_hdb_budget(cash_savings, cpf_savings, max_loan)
    
    if total_budget >= bto_price:
        status = "Affordable"
    else:
        shortfall = bto_price - total_budget
        status = f"Shortfall: ${shortfall:,.2f}"
    
    return {
        "max_hdb_loan": max_loan,
        "total_budget": total_budget,
        "affordability_status": status
    }

# -------------------------------
# bedrock model setup
# -------------------------------
session = boto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    aws_session_token=AWS_SESSION_TOKEN,
    region_name=AWS_REGION
)

model = BedrockModel(
    model_id=BEDROCK_MODEL_ID,
    max_tokens=1024,
    boto_client_config=Config(
        read_timeout=120,
        connect_timeout=120,
        retries=dict(max_attempts=3, mode="adaptive")
    ),
    boto_session=session
)

# -------------------------------
# main agent setup
# -------------------------------
SYSTEM_PROMPT = """
You are a Singapore HDB loan affordability assistant.

You can:
- Calculate the maximum HDB loan based on household income, cash savings, and CPF
- Calculate total budget including max loan, cash, and CPF
- Provide affordability status against a given BTO price
- Present results clearly and simply
"""

loan_agent = Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=[estimate_hdb_loan_with_budget],
    callback_handler=PrintingCallbackHandler()
)

# -------------------------------
# demo / test run
# -------------------------------

def main():
    print("Welcome to the HDB Loan & Budget Estimator!\n")

    # ask user for input
    household_income = int(input("Enter your monthly household income: "))
    cash_savings = float(input("Enter your cash savings: "))
    cpf_savings = float(input("Enter your CPF savings: "))
    bto_price = float(input("Enter the BTO price you are considering: "))

    # create prompt for agent
    prompt = (
        f"My household income is {household_income}, "
        f"cash savings ${cash_savings}, CPF ${cpf_savings}, "
        f"interested in a BTO costing ${bto_price}. "
        f"Please estimate my HDB loan and affordability."
    )

    # call the agent
    print("\nCalculating...\n")
    response = loan_agent(prompt)

    # optionally, keep demoing more queries
    while True:
        cont = input("\nDo you want to try another scenario? (y/n): ").strip().lower()
        if cont != "y":
            break

        household_income = int(input("Enter your monthly household income: "))
        cash_savings = float(input("Enter your cash savings: "))
        cpf_savings = float(input("Enter your CPF savings: "))
        bto_price = float(input("Enter the BTO price you are considering: "))

        prompt = (
            f"My household income is {household_income}, "
            f"cash savings ${cash_savings}, CPF ${cpf_savings}, "
            f"interested in a BTO costing ${bto_price}. "
            f"Please estimate my HDB loan and affordability."
        )

        print("\nCalculating...\n")
        response = loan_agent(prompt)

if __name__ == "__main__":
    main()

test_cases = [ 
    {"household_income": 9000, "cash_savings": 20000, "cpf_savings": 50000, "bto_price": 350000,},
    {"household_income": 7000, "cash_savings": 10000, "cpf_savings": 30000, "bto_price": 400000,},
    {"household_income": 12000, "cash_savings": 50000, "cpf_savings": 80000, "bto_price": 450000,},
    ]