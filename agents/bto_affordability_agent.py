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
# new: affordability against estimate dict with CI
# -------------------------------

def assess_estimate_item(total_budget: float, item: dict) -> dict:
    """assess affordability for one estimate entry with CI

    item is expected to contain keys: estimatedPrice, ciLower, ciUpper, projectLocation, flatType.
    all numeric fields are optional and handled gracefully.
    """
    est = item.get("estimatedPrice")
    lo = item.get("ciLower")
    hi = item.get("ciUpper")
    # compute primary status vs estimated price
    primary = assess_bto_affordability(total_budget, float(est) if est is not None else float('inf'))
    margin = None if est is None else round(total_budget - float(est), 2)
    # confidence narrative using CI
    confidence = "unknown"
    if lo is not None and hi is not None:
        if total_budget >= hi:
            confidence = "likely_affordable"
        elif total_budget < lo:
            confidence = "likely_unaffordable"
        else:
            confidence = "borderline"
    elif lo is not None:
        confidence = "likely_affordable" if total_budget >= lo else "likely_unaffordable"
    elif hi is not None:
        confidence = "likely_affordable" if total_budget >= hi else "borderline"

    # build explanation string
    def fmt(x):
        try:
            return f"${float(x):,.0f}"
        except Exception:
            return "N/A"

    parts = []
    parts.append(f"Budget {fmt(total_budget)} vs estimate {fmt(est)}.")
    if lo is not None or hi is not None:
        parts.append(f"95% CI: {fmt(lo)} - {fmt(hi)}.")
    if confidence == "likely_affordable":
        parts.append("Your budget exceeds the upper bound, suggesting comfortable affordability.")
    elif confidence == "likely_unaffordable":
        parts.append("Your budget is below the lower bound; affordability is unlikely.")
    elif confidence == "borderline":
        parts.append("Your budget intersects the CI; outcome is uncertain and depends on final pricing.")
    else:
        parts.append("Unable to assess confidence due to missing CI.")

    # compose result
    result = {
        "affordability_status": primary["affordability_status"],
        "shortfall": primary.get("shortfall", 0.0),
        "margin_vs_estimate": margin,
        "confidence": confidence,
        "explanation": " ".join(parts),
    }
    return result


def assess_estimates_with_budget(total_budget: float, estimates: dict) -> dict:
    """assess all items in a results dict from cost estimator.

    estimates: { id: { projectLocation, flatType, estimatedPrice, ciLower, ciUpper, ... } }
    returns: { id: { affordability_status, shortfall, margin_vs_estimate, confidence, explanation } }
    """
    output = {}
    for key, item in (estimates or {}).items():
        try:
            output[key] = assess_estimate_item(total_budget, item)
        except Exception as e:
            logger.warning(f"Affordability assessment failed for id={key}: {e}")
            output[key] = {
                "affordability_status": "error",
                "shortfall": None,
                "margin_vs_estimate": None,
                "confidence": "unknown",
                "explanation": "Unable to assess due to error.",
            }
    return output

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
