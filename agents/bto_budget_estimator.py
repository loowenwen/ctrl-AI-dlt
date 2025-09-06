"""
budget estimation helpers for HDB affordability workflows

expose small, importable functions so other modules (agents, APIs) can reuse
the same logic without duplication.
"""

# -------------------------------
# Financial calculation helpers
# -------------------------------
def max_hdb_loan_from_income(income, annual_rate=0.03, years=25):
    """compute max HDB loan based on monthly household income.

    assumptions:
    - 30% of monthly income goes to mortgage payment
    - fixed-rate amortization with given rate and tenure
    """
    monthly_payment = 0.3 * income  # 30% of household income
    r = annual_rate / 12.0
    N = years * 12
    factor = (1 + r) ** N
    loan = monthly_payment * (factor - 1) / (r * factor)
    return round(loan, 2)


def total_hdb_budget(cash_savings, cpf_savings, max_loan):
    """total available budget including cash + CPF + loan."""
    return round(cash_savings + cpf_savings + max_loan, 2)


def compute_total_budget(
    *,
    household_income: float,
    cash_savings: float,
    cpf_savings: float,
    annual_rate: float = 0.03,
    tenure_years: int = 25,
):
    """convenience function to compute max loan and total budget.

    returns a dict with keys: max_hdb_loan, total_budget
    """
    max_loan = max_hdb_loan_from_income(household_income, annual_rate, tenure_years)
    total_budget_val = total_hdb_budget(cash_savings, cpf_savings, max_loan)
    return {
        "max_hdb_loan": max_loan,
        "total_budget": total_budget_val,
    }
