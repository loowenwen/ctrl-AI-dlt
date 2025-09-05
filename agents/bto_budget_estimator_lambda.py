"""
AWS Lambda handler for the HDB Loan & Budget Estimator.

This wraps the existing agent in `agents/bto_budget_estimator_agent.py`
and adapts input/output for Lambda. It preserves the original logic and
model setup, only changing how inputs are received and outputs returned.

Event example:
{
  "household_income": 9000,
  "cash_savings": 20000,
  "cpf_savings": 50000,
  "bto_price": 350000,
  "annual_rate": 0.03,           # optional
  "tenure_years": 25             # optional
}

Response example:
{
  "ok": true,
  "input": { ...echo of sanitized inputs... },
  "calculation": {
    "max_hdb_loan": 123456.0,
    "total_budget": 234567.0,
    "affordability_status": "Affordable | Shortfall: $X"
  },
  "agent_response_text": "...LLM response string..."
}
"""

from __future__ import annotations

import os
import json
from typing import Any, Dict

# Import the existing agent and tool without modifying them
from agents.bto_budget_estimator_agent import (
    loan_agent,
    estimate_hdb_loan_with_budget,
)


def _sanitize_float(value: Any, name: str) -> float:
    try:
        return float(value)
    except Exception:
        raise ValueError(f"Invalid value for {name}: {value}")


def _sanitize_int(value: Any, name: str) -> int:
    try:
        return int(value)
    except Exception:
        raise ValueError(f"Invalid value for {name}: {value}")


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda entrypoint."""
    try:
        # Read inputs from event
        household_income = _sanitize_int(event.get("household_income"), "household_income")
        cash_savings = _sanitize_float(event.get("cash_savings"), "cash_savings")
        cpf_savings = _sanitize_float(event.get("cpf_savings"), "cpf_savings")
        bto_price = _sanitize_float(event.get("bto_price"), "bto_price")

        annual_rate = float(event.get("annual_rate", 0.03))
        tenure_years = int(event.get("tenure_years", 25))

        # Build the same style of prompt used in the CLI version
        prompt = (
            f"My household income is {household_income}, "
            f"cash savings ${cash_savings}, CPF ${cpf_savings}, "
            f"interested in a BTO costing ${bto_price}. "
            f"Please estimate my HDB loan and affordability."
        )

        # Get a natural-language response from the agent (uses Bedrock)
        agent_response_text = str(loan_agent(prompt))

        # Also compute the structured calculation via the tool directly for JSON output
        calculation = estimate_hdb_loan_with_budget(
            household_income=household_income,
            cash_savings=cash_savings,
            cpf_savings=cpf_savings,
            bto_price=bto_price,
            annual_rate=annual_rate,
            tenure_years=tenure_years,
        )

        return {
            "ok": True,
            "input": {
                "household_income": household_income,
                "cash_savings": cash_savings,
                "cpf_savings": cpf_savings,
                "bto_price": bto_price,
                "annual_rate": annual_rate,
                "tenure_years": tenure_years,
            },
            "calculation": calculation,
            "agent_response_text": agent_response_text,
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
        }

