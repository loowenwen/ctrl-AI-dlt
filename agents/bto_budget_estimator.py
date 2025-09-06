"""
budget estimation helpers for HDB affordability workflows

expose small, importable functions so other modules (agents, APIs) can reuse
the same logic without duplication.
"""

# -------------------------------
# Financial calculation helpers
# -------------------------------
def max_hdb_loan_from_income(income, annual_rate=0.03, years=25):
    """compute max HDB loan based on monthly household income

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


def total_hdb_budget(cash_savings, cpf_savings, max_loan, retain_oa_amount: float = 20000.0):
    """total available budget including cash + CPF (after retention) + loan

    by default, retain $20,000 in CPF OA as a safety buffer
    """
    retained = max(min(retain_oa_amount, cpf_savings), 0.0)
    cpf_used = max(cpf_savings - retained, 0.0)
    total = cash_savings + cpf_used + max_loan
    return round(total, 2), round(cpf_used, 2), round(retained, 2)


def compute_total_budget(
    *,
    household_income: float,
    cash_savings: float,
    cpf_savings: float,
    annual_rate: float = 0.03,
    tenure_years: int = 25,
    retain_oa_amount: float = 20000.0,
):
    """convenience function to compute max loan and total budget.

    returns a dict with keys: max_hdb_loan, total_budget
    """
    max_loan = max_hdb_loan_from_income(household_income, annual_rate, tenure_years)
    total_budget_val, cpf_used, retained = total_hdb_budget(
        cash_savings, cpf_savings, max_loan, retain_oa_amount
    )
    return {
        "max_hdb_loan": max_loan,
        "total_budget": total_budget_val,
        "cpf_used_in_budget": cpf_used,
        "retained_oa": retained,
    }
