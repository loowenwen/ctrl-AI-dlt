"""
AWS Lambda handler for the Enhanced BTO Cost Estimator.

This wraps the existing estimator in `agents/bto_cost_estimator_agent.py`
and adapts input/output for Lambda without changing core logic.

Event example:
{
  "project_location": "queenstown",
  "flat_type": "4-room",
  "exercise_date": "2025-10-01",      # optional (default "2025-10-01")
  "project_name": "Ulu Pandan Vista",  # optional
  "csv_path": "bto_pricing_detail_cleaned.csv"  # optional
}

Response example:
{
  "ok": true,
  "estimate": {
    "flat_type": "4-room",
    "project_location": "queenstown",
    "project_tier": "Prime",
    "exercise_date": "2025-10-01",
    "estimated_price": 650000.0,
    "confidence_interval": [600000.0, 700000.0],
    "sample_size": 42,
    "historical_trend": "increasing",
    "methodology": "linear_regression"
  }
}
"""

from __future__ import annotations

import os
from typing import Any, Dict

from agents.bto_cost_estimator_agent import EnhancedBTOCostEstimator, PriceEstimate


def _default_csv_path(event_csv: str | None) -> str:
    if event_csv:
        return event_csv
    # Prefer co-located CSV in repo root when packaged into Lambda.
    # Resolve relative to this file: agents/ -> repo_root/../bto_pricing_detail_cleaned.csv
    here = os.path.dirname(__file__)
    root = os.path.abspath(os.path.join(here, os.pardir))
    candidate = os.path.join(root, "bto_pricing_detail_cleaned.csv")
    return candidate


def _estimate_to_dict(estimate: PriceEstimate) -> Dict[str, Any]:
    return {
        "flat_type": estimate.flat_type,
        "project_location": estimate.project_location,
        "project_tier": estimate.project_tier,
        "exercise_date": estimate.exercise_date,
        "estimated_price": estimate.estimated_price,
        "confidence_interval": list(estimate.confidence_interval) if estimate.confidence_interval else None,
        "sample_size": estimate.sample_size,
        "historical_trend": estimate.historical_trend,
        "methodology": estimate.methodology,
    }


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        project_location = (event.get("project_location") or "").strip()
        flat_type = (event.get("flat_type") or "").strip()
        exercise_date = (event.get("exercise_date") or "2025-10-01").strip()
        project_name = (event.get("project_name") or None)
        csv_path = _default_csv_path(event.get("csv_path"))

        if not project_location:
            raise ValueError("`project_location` is required")
        if not flat_type:
            raise ValueError("`flat_type` is required")

        estimator = EnhancedBTOCostEstimator(csv_path)
        estimate = estimator.estimate_cost(
            project_location=project_location,
            flat_type=flat_type,
            exercise_date=exercise_date,
            project_name=project_name,
        )

        return {
            "ok": True,
            "estimate": _estimate_to_dict(estimate),
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
        }

