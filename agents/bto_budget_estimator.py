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