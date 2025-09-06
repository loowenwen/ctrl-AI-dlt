import os
import logging
from dotenv import load_dotenv
from botocore.config import Config
import boto3
from strands import Agent, tool
from strands.handlers.callback_handler import PrintingCallbackHandler
from strands.models.bedrock import BedrockModel
from .bto_budget_estimator import (
    max_hdb_loan_from_income,
    total_hdb_budget,
    compute_total_budget,
)

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
# affordability helpers (using budget estimator)
# -------------------------------
def assess_bto_affordability(total_budget: float, bto_price: float):
    """Assess affordability for a single BTO price against total budget."""
    if total_budget >= bto_price:
        return {
            "affordability_status": "Affordable",
            "shortfall": 0.0,
        }
    shortfall = round(bto_price - total_budget, 2)
    return {
        "affordability_status": f"Shortfall: ${shortfall:,.2f}",
        "shortfall": shortfall,
    }

def assess_bto_list(total_budget: float, btos: list):
    """Assess a list of BTOs where each item has {name, price}.

    Returns a list of {name, price, affordability_status, shortfall}.
    """
    results = []
    for item in btos:
        name = item.get("name")
        price = float(item.get("price", 0))
        res = assess_bto_affordability(total_budget, price)
        results.append({
            "name": name,
            "price": price,
            **res,
        })
    return results

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
    comp = compute_total_budget(
        household_income=household_income,
        cash_savings=cash_savings,
        cpf_savings=cpf_savings,
        annual_rate=annual_rate,
        tenure_years=tenure_years,
    )
    max_loan = comp["max_hdb_loan"]
    total_budget = comp["total_budget"]
    status_info = assess_bto_affordability(total_budget, bto_price)
    status = status_info["affordability_status"]
    
    return {
        "max_hdb_loan": max_loan,
        "total_budget": total_budget,
        "affordability_status": status
    }

@tool
def assess_affordability_with_budget(
    total_budget: float,
    bto_price: float,
):
    """Assess affordability given a pre-computed total budget and a BTO price."""
    info = assess_bto_affordability(total_budget, bto_price)
    return {
        "total_budget": round(total_budget, 2),
        "bto_price": round(bto_price, 2),
        **info,
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
    tools=[estimate_hdb_loan_with_budget, assess_affordability_with_budget],
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
