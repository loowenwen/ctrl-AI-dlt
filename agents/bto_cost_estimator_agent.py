import argparse
import os
import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple

import pandas as pd
from strands import Agent
from strands.models import BedrockModel


@dataclass
class EstimateResult:
    flat_type: str
    project_location: str
    min_price: Optional[float]
    median_price: Optional[float]
    max_price: Optional[float]
    sample_size: int


class BTOPricingEstimator:
    """
    Estimate BTO flat prices by flat type and project location using BTO_Pricing.csv.

    Expected CSV columns (case-insensitive match by normalized names):
    - flat_type
    - project_location (or town/estate)
    - price or min_price/median_price/max_price
    """

    def __init__(self, csv_path: str) -> None:
        if not os.path.isabs(csv_path):
            csv_path = os.path.abspath(csv_path)
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV not found: {csv_path}")
        self.csv_path = csv_path
        self.df = self._load_and_normalize(csv_path)

    @staticmethod
    def _normalize_col(name: str) -> str:
        return name.strip().lower().replace(" ", "_")

    def _load_and_normalize(self, path: str) -> pd.DataFrame:
        df = pd.read_csv(path)
        df = df.rename(columns={c: self._normalize_col(c) for c in df.columns})

        # Try to standardize location column naming
        if "project_location" not in df.columns:
            for candidate in ["location", "town", "estate", "project", "area"]:
                if candidate in df.columns:
                    df = df.rename(columns={candidate: "project_location"})
                    break

        # Try to standardize price columns
        has_min = "min_price" in df.columns
        has_median = "median_price" in df.columns
        has_max = "max_price" in df.columns
        if not (has_min and has_median and has_max):
            # If there is a single price column, treat it as median
            for candidate in ["price", "avg_price", "average_price", "mean_price"]:
                if candidate in df.columns:
                    df = df.rename(columns={candidate: "median_price"})
                    has_median = True
                    break

        # Ensure required columns exist
        required = ["flat_type", "project_location", "median_price"]
        for col in required:
            if col not in df.columns:
                df[col] = pd.NA

        # Coerce price fields to numeric
        for col in ["min_price", "median_price", "max_price"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Parse temporal columns if available
        time_candidates: List[str] = [
            "launch_date",
            "release_date",
            "application_date",
            "sales_launch",
            "date",
            "year",
        ]
        parsed_time_col = None
        for c in time_candidates:
            if c in df.columns:
                if c == "year":
                    # Handle year-only as datetime (Jan 1 of that year)
                    df[c] = pd.to_numeric(df[c], errors="coerce")
                    df["__parsed_date"] = pd.to_datetime(df[c], format="%Y", errors="coerce")
                else:
                    df["__parsed_date"] = pd.to_datetime(df[c], errors="coerce", utc=True).dt.tz_localize(None)
                parsed_time_col = "__parsed_date"
                break

        # If no date parsed, leave as None; downstream will fallback
        df[parsed_time_col] = df[parsed_time_col] if parsed_time_col else pd.NaT

        # Normalize text columns
        for col in ["flat_type", "project_location"]:
            if col in df.columns:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                )

        return df

    def estimate_cost(self, flat_type: str, project_location: str) -> EstimateResult:
        ft = flat_type.strip().lower()
        loc = project_location.strip().lower()

        subset = self.df
        if ft:
            subset = subset[subset["flat_type"] == ft]
        if loc:
            subset = subset[subset["project_location"].str.contains(loc, na=False)]

        sample_size = len(subset)
        if sample_size == 0:
            return EstimateResult(
                flat_type=flat_type,
                project_location=project_location,
                min_price=None,
                median_price=None,
                max_price=None,
                sample_size=0,
            )

        min_price = subset["min_price"].min(skipna=True) if "min_price" in subset else None
        median_price = subset["median_price"].median(skipna=True) if "median_price" in subset else None
        max_price = subset["max_price"].max(skipna=True) if "max_price" in subset else None

        return EstimateResult(
            flat_type=flat_type,
            project_location=project_location,
            min_price=float(min_price) if pd.notna(min_price) else None,
            median_price=float(median_price) if pd.notna(median_price) else None,
            max_price=float(max_price) if pd.notna(max_price) else None,
            sample_size=sample_size,
        )

    def estimate_with_trend(self, flat_type: str, project_location: str) -> EstimateResult:
        """Estimate using latest median and a simple time-trend projection if timestamps exist.

        Trend logic:
        - If a parsed date column exists for matching records, fit a simple linear trend on median_price vs date ordinal.
        - Predict one time step beyond the latest point (approx 1 month) as a proxy for next release.
        - If no dates or insufficient points, apply a modest uplift (e.g., 3%).
        """
        base = self.estimate_cost(flat_type, project_location)
        # If we lack sample or median, just return base
        if base.sample_size == 0 or base.median_price is None:
            return base

        ft = flat_type.strip().lower()
        loc = project_location.strip().lower()
        subset = self.df
        subset = subset[(subset["flat_type"] == ft) & (subset["project_location"].str.contains(loc, na=False))]

        if "__parsed_date" in subset.columns and subset["__parsed_date"].notna().sum() >= 3 and subset["median_price"].notna().sum() >= 3:
            # Prepare data for regression
            s = subset.dropna(subset=["__parsed_date", "median_price"]).copy()
            if len(s) >= 3:
                x = s["__parsed_date"].map(pd.Timestamp.toordinal).astype(float)
                y = s["median_price"].astype(float)
                # Simple linear fit
                try:
                    coeffs = pd.Series(y).polyfit(x, deg=1)
                    slope, intercept = float(coeffs[0]), float(coeffs[1])
                    next_x = float(s["__parsed_date"].max().toordinal() + 30)  # approx +30 days
                    projected = slope * next_x + intercept
                    # Clamp unreasonable projections
                    if projected > 0 and projected < base.median_price * 1.8:
                        return EstimateResult(
                            flat_type=flat_type,
                            project_location=project_location,
                            min_price=base.min_price,
                            median_price=float(projected),
                            max_price=base.max_price,
                            sample_size=base.sample_size,
                        )
                except Exception:
                    pass

        # Fallback modest uplift
        uplifted = float(base.median_price * 1.03)
        return EstimateResult(
            flat_type=flat_type,
            project_location=project_location,
            min_price=base.min_price,
            median_price=uplifted,
            max_price=base.max_price,
            sample_size=base.sample_size,
        )


def _default_csv_path() -> str:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, "BTO_Pricing.csv")


def run_cli(argv: Optional[Tuple[str, ...]] = None) -> int:
    parser = argparse.ArgumentParser(description="BTO Cost Estimator")
    parser.add_argument("--flat-type", required=True, help="Flat type, e.g., 2-room, 3-room, 4-room, 5-room")
    parser.add_argument("--location", required=True, help="Project location keyword, e.g., Toa Payoh")
    parser.add_argument("--csv", default=_default_csv_path(), help="Path to BTO_Pricing.csv")

    args = parser.parse_args(args=list(argv) if argv is not None else None)

    estimator = BTOPricingEstimator(csv_path=args.csv)
    result = estimator.estimate_cost(flat_type=args.flat_type, project_location=args.location)

    # Print concise summary
    print("BTO Cost Estimate")
    print(f"- Flat Type: {result.flat_type}")
    print(f"- Location: {result.project_location}")
    print(f"- Samples: {result.sample_size}")
    if result.sample_size == 0:
        print("No matching records found.")
        return 1
    if result.min_price is not None:
        print(f"- Min Price: ${result.min_price:,.0f}")
    if result.median_price is not None:
        print(f"- Median Price: ${result.median_price:,.0f}")
    if result.max_price is not None:
        print(f"- Max Price: ${result.max_price:,.0f}")
    return 0


def estimate_bto_cost(flat_type: str, project_location: str, csv_path: Optional[str] = None) -> EstimateResult:
    """Convenience function for use by other modules/notebooks."""
    estimator = BTOPricingEstimator(csv_path=csv_path or _default_csv_path())
    return estimator.estimate_cost(flat_type=flat_type, project_location=project_location)


# ----------------------
# LLM classification + chat
# ----------------------

def _maybe_web_search(query: str) -> str:
    """Optional web search using Tavily if available; returns textual context or empty string."""
    try:
        from tavily import TavilyClient  # type: ignore
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            return ""
        client = TavilyClient(api_key=api_key)
        res = client.search(query=query, max_results=3)
        if isinstance(res, dict) and "results" in res:
            snippets = []
            for r in res.get("results", [])[:3]:
                snippet = r.get("content") or r.get("snippet") or ""
                if snippet:
                    snippets.append(str(snippet))
            return "\n\n".join(snippets)
        return ""
    except Exception:
        return ""


CLASSIFY_SYSTEM_PROMPT = """
You are an HDB BTO project classifier. Classify a project into EXACTLY ONE of: Standard, Plus, Prime.

Rules summary:
- Prime: Very central, near city center, high-demand/amenity locations (e.g., Queenstown, Kallang/Whampoa, Bukit Merah).
- Plus: Attractive or nearer to transport/amenities, but not the most central (e.g., matured towns near MRT hubs).
- Standard: Typical estates without special centrality or premium restrictions.

Return strictly one of: "Standard", "Plus", or "Prime". Do not include any other text.
"""


def classify_project_tier(location: str, flat_type: str, model_id: str = "us.amazon.nova-lite-v1:0") -> str:
    model = BedrockModel(model_id=model_id, temperature=0.2)
    agent = Agent(model=model, system_prompt=CLASSIFY_SYSTEM_PROMPT)
    web_context = _maybe_web_search(f"HDB BTO location context: {location}")
    prompt = (
        f"Location: {location}\n"
        f"Flat Type: {flat_type}\n"
        f"Context (optional):\n{web_context}\n\n"
        f"Classify as exactly one label."
    )
    out = str(agent(prompt)).strip()
    out_lower = out.lower()
    if "prime" in out_lower:
        return "Prime"
    if "plus" in out_lower:
        return "Plus"
    return "Standard"


def interactive_chat(csv_path: Optional[str] = None, model_id: str = "us.amazon.nova-lite-v1:0") -> None:
    print("\nBTO Cost Estimator (interactive). Type 'exit' at any prompt to quit.\n")
    estimator = BTOPricingEstimator(csv_path=csv_path or _default_csv_path())
    while True:
        loc = input("Project location: ").strip()
        if not loc or loc.lower() in ("exit", "quit"):
            break
        ft = input("Flat type (e.g., 2-room, 3-room, 4-room, 5-room): ").strip()
        if not ft or ft.lower() in ("exit", "quit"):
            break

        print("\nClassifying project tier (Standard/Plus/Prime)...")
        try:
            tier = classify_project_tier(location=loc, flat_type=ft, model_id=model_id)
        except Exception as e:
            tier = "Standard"
        print(f"Tier: {tier}")

        print("Estimating price with time-trend adjustment...")
        trended = estimator.estimate_with_trend(flat_type=ft, project_location=loc)

        print("\nResult")
        print(f"- Location: {loc}")
        print(f"- Flat Type: {ft}")
        print(f"- Classified Tier: {tier}")
        print(f"- Samples: {trended.sample_size}")
        if trended.sample_size == 0:
            print("No matching historical records found in CSV.")
        if trended.min_price is not None:
            print(f"- Historical Min: ${trended.min_price:,.0f}")
        if trended.median_price is not None:
            print(f"- Projected Median (next release): ${trended.median_price:,.0f}")
        if trended.max_price is not None:
            print(f"- Historical Max: ${trended.max_price:,.0f}")
        print("")


if __name__ == "__main__":
    # If no additional CLI args are passed, start interactive chat.
    if len(sys.argv) == 1:
        interactive_chat()
    else:
        sys.exit(run_cli())


