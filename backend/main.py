from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
import json
from pathlib import Path

# Reuse budget computation helpers
from agents.bto_budget_estimator import compute_total_budget
from agents.bto_cost_estimator_agent import (
    run_estimates_for_selection,
    EnhancedBTOCostEstimator,
)
from agents.bto_affordability_agent import assess_estimates_with_budget
from agents.bto_launch_websearch_agent import run as launch_websearch
from agents.bto_transport import analyze_bto_transport, compare_bto_transports, get_bto_locations, clear_comparison_data, analyze_all_bto_transports, get_comparison_history





app = FastAPI()

# Enable CORS so frontend (React) can call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# BTO data endpoint
@app.get("/bto-data")
def get_bto_data():
    try:
        with open('data/oct25_bto.json', 'r') as f:
            data = json.load(f)
            return data
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="BTO data file not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Error parsing BTO data file")

# Price estimation endpoint
@app.get("/estimate-price/{project_name}/{flat_type}")
def estimate_price(project_name: str, flat_type: str):
    try:
        estimator = EnhancedBTOCostEstimator("data/bto_pricing_detail_cleaned.csv")
        price_range = estimator.get_price_range(project_name, flat_type)
        
        print(f"Price estimation for {project_name} {flat_type}: {price_range}")
        
        # Parse price range like "350k-400k" to get average
        if price_range and 'k' in price_range:
            range_parts = price_range.replace('k', '').split('-')
            if len(range_parts) == 2:
                min_price = float(range_parts[0]) * 1000
                max_price = float(range_parts[1]) * 1000
                estimated_price = (min_price + max_price) / 2
            else:
                # Single value like "350k"
                estimated_price = float(range_parts[0]) * 1000
        else:
            # Use different defaults based on flat type if estimation fails
            flat_type_defaults = {
                "2-Room": 250000,
                "3-Room": 350000,
                "4-Room": 450000,
                "5-Room": 550000,
                "3Gen": 600000
            }
            estimated_price = flat_type_defaults.get(flat_type, 400000)
            price_range = f"{int(estimated_price*0.9/1000)}k-{int(estimated_price*1.1/1000)}k"
            
        return {
            "estimated_price": int(estimated_price),
            "price_range": price_range,
            "project_name": project_name,
            "flat_type": flat_type
        }
    except Exception as e:
        print(f"Error estimating price for {project_name} {flat_type}: {str(e)}")
        # Return different defaults based on flat type
        flat_type_defaults = {
            "2-Room": 250000,
            "3-Room": 350000,
            "4-Room": 450000,
            "5-Room": 550000,
            "3Gen": 600000
        }
        estimated_price = flat_type_defaults.get(flat_type, 400000)
        return {
            "estimated_price": estimated_price,
            "price_range": f"{int(estimated_price*0.9/1000)}k-{int(estimated_price*1.1/1000)}k",
            "project_name": project_name,
            "flat_type": flat_type,
            "fallback": True
        }

# Define request schema
class UserInfo(BaseModel):
    age: int
    income: float
    family_size: int

# Example agent function: eligibility checker
def eligibility_agent(user_info):
    if user_info.age >= 21 and user_info.income <= 120000:
        return {"eligible": True, "message": "You may qualify for BTO grants."}
    else:
        return {"eligible": False, "message": "You may not qualify for BTO grants."}

# API endpoint to call the agent
@app.post("/check_eligibility")
def check_eligibility(user_info: UserInfo):
    result = eligibility_agent(user_info)
    return result

# Optional: simple homepage so / doesn't 404
@app.get("/")
def read_root():
    return {"message": "Welcome to BTO Eligibility API"}


# -------------------------------
# Budget + Affordability endpoints
# -------------------------------

# Simple in-memory store for demo purposes. For multi-user, key by session/user id.
BUDGET_STORE: Dict[str, Dict[str, Any]] = {}


class BudgetRequest(BaseModel):
    household_income: float = Field(..., description="Monthly household income")
    cash_savings: float = Field(..., description="Cash savings available")
    cpf_savings: float = Field(..., description="CPF OA savings available")
    annual_rate: float = Field(0.03, description="Annual interest rate")
    tenure_years: int = Field(25, description="Loan tenure in years")
    retain_oa_amount: float = Field(20000.0, description="CPF OA to retain as buffer")
    session_id: Optional[str] = Field(None, description="Optional key to store budget server-side")


class BudgetResponse(BaseModel):
    max_hdb_loan: float
    total_budget: float
    cpf_used_in_budget: Optional[float] = None
    retained_oa: Optional[float] = None
    session_id: Optional[str] = None


@app.post("/budget", response_model=BudgetResponse)
def calculate_budget(req: BudgetRequest):
    try:
        result = compute_total_budget(
            household_income=req.household_income,
            cash_savings=req.cash_savings,
            cpf_savings=req.cpf_savings,
            annual_rate=req.annual_rate,
            tenure_years=req.tenure_years,
            retain_oa_amount=req.retain_oa_amount,
        )
        if req.session_id:
            BUDGET_STORE[req.session_id] = result
        return {**result, "session_id": req.session_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class BTOItem(BaseModel):
    name: str
    flatType: str
    price: float


class AffordabilityRequest(BaseModel):
    # Either provide total_budget directly or reference a stored session_id
    total_budget: Optional[float] = None
    session_id: Optional[str] = None
    btos: List[BTOItem]


class AffordabilityItem(BaseModel):
    name: str
    flatType: str
    price: float
    affordability_status: str
    shortfall: float
    monthly_payment: Optional[float] = None
    downpayment_needed: Optional[float] = None
    project_tier: Optional[str] = None
    additional_requirements: Optional[str] = None
    potential_grants: Optional[List[str]] = None


class AffordabilityResponse(BaseModel):
    total_budget: float
    max_monthly_payment: float
    results: List[AffordabilityItem]


@app.post("/affordability", response_model=AffordabilityResponse)
def check_affordability(req: AffordabilityRequest):
    # Resolve budget
    budget: Optional[float] = req.total_budget
    if budget is None and req.session_id:
        stored = BUDGET_STORE.get(req.session_id)
        if stored:
            budget = float(stored.get("total_budget", 0.0))
    if budget is None:
        raise HTTPException(status_code=400, detail="Provide total_budget or a valid session_id")

    # Get the cost estimator for tier classification
    cost_estimator = EnhancedBTOCostEstimator("data/bto_pricing_detail_cleaned.csv")
    
    # Compute affordability per BTO
    results: List[AffordabilityItem] = []
    # Calculate max monthly payment (30% rule of thumb for mortgage affordability)
    max_monthly = budget * 0.03  # 3% of total budget approximates monthly payment
    
    for b in req.btos:
        # Get project tier for classification
        try:
            project_tier = cost_estimator.classifier.classify(b.name)
        except:
            project_tier = "Standard"  # Default if classification fails
        
        # Calculate monthly payment (rough estimate: 25 years, 2.6% interest)
        try:
            monthly_payment = round((b.price * 0.026 / 12) / (1 - (1 + 0.026 / 12) ** -300), 2)
        except:
            monthly_payment = round(b.price / 300, 2)  # Fallback simple calculation
            
        downpayment = round(b.price * 0.15, 2)  # 15% downpayment
        
        # Check affordability
        if budget >= b.price:
            if monthly_payment <= max_monthly:
                status = "Affordable"
                shortfall = 0.0
            else:
                status = "Not Affordable"
                shortfall = 0.0  # Budget is enough but monthly payment is too high
        else:
            shortfall = round(b.price - budget, 2)
            status = "Not Affordable"
        
        # Determine potential grants
        grants = []
        if project_tier != "Prime":
            grants.append("Enhanced CPF Housing Grant (Up to $80,000)")
            if project_tier == "Standard":
                grants.append("Additional Subsidies for Non-Mature Estates")
        
        # Additional requirements for Prime/Plus locations
        additional_reqs = None
        if project_tier == "Prime":
            additional_reqs = "Subject to 6-year MOP and subsidy clawback"
        elif project_tier == "Plus":
            additional_reqs = "Subject to 6-year MOP"
        
        results.append(AffordabilityItem(
            name=b.name,
            flatType=b.flatType,
            price=b.price,
            affordability_status=status,
            shortfall=shortfall,
            monthly_payment=monthly_payment,
            downpayment_needed=downpayment,
            project_tier=project_tier,
            additional_requirements=additional_reqs,
            potential_grants=grants,
        ))

    # Calculate max monthly payment (30% of budget as a rough guideline)
    max_monthly = round(budget * 0.03, 2)  # 3% of total budget as max monthly payment
    
    return AffordabilityResponse(
        total_budget=round(budget, 2),
        max_monthly_payment=max_monthly,
        results=results
    )


# -------------------------------
# BTO data endpoints
# -------------------------------

@app.get("/bto-data")
def get_bto_data():
    """Return the BTO project data for frontend."""
    try:
        return _load_bto_json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/estimate-price/{project_name}/{flat_type}")
def estimate_price(project_name: str, flat_type: str):
    """Get price estimate for a BTO project and flat type."""
    try:
        # Initialize cost estimator
        estimator = EnhancedBTOCostEstimator("data/bto_pricing_detail_cleaned.csv")
        
        # Get project tier
        tier = estimator.classifier.classify(project_name)
        
        # Filter data by flat type and tier
        filtered_df = estimator._filter_data(flat_type, tier)
        
        # Get average price for similar units
        if len(filtered_df) > 0:
            avg_price = filtered_df['median_price'].mean()
            min_price = filtered_df['median_price'].min()
            max_price = filtered_df['median_price'].max()
            
            return {
                "estimated_price": round(avg_price, 2),
                "price_range": {
                    "min": round(min_price, 2),
                    "max": round(max_price, 2)
                },
                "project_tier": tier
            }
        else:
            raise HTTPException(
                status_code=404, 
                detail=f"No price data available for {flat_type} in {project_name}"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------
# BTO listings endpoint (for mapping)
# -------------------------------


class BTOListing(BaseModel):
    lat: float
    lng: float
    town: str
    flatType: str
    projectId: Optional[str] = None
    region: Optional[str] = None
    listingType: Optional[str] = None
    stage: Optional[str] = None
    ballotQtr: Optional[str] = None


def _load_bto_json() -> List[Dict[str, Any]]:
    """load raw BTO data file from data directory."""
    data_path = Path(__file__).resolve().parent.parent / "data" / "oct25_bto.json"
    if not data_path.exists():
        raise FileNotFoundError(f"Cannot find data file: {data_path}")
    with data_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _normalize_bto_items(raw_items: List[Dict[str, Any]]) -> List[BTOListing]:
    """convert raw items into a frontend-friendly list with lat/lng and key fields."""
    normalized: List[BTOListing] = []
    for item in raw_items:
        coords_raw = item.get("coordinates")
        lat, lng = None, None
        if isinstance(coords_raw, str):
            # Stored as string like "[1.3772, 103.8525]"
            try:
                parsed = json.loads(coords_raw)
                if isinstance(parsed, list) and len(parsed) == 2:
                    lat, lng = float(parsed[0]), float(parsed[1])
            except Exception:
                pass
        elif isinstance(coords_raw, list) and len(coords_raw) == 2:
            lat, lng = float(coords_raw[0]), float(coords_raw[1])

        props = (item.get("properties") or {})
        desc_list = props.get("description") or []
        desc = desc_list[0] if desc_list else {}

        normalized.append(BTOListing(
            lat=lat if lat is not None else 0.0,
            lng=lng if lng is not None else 0.0,
            town=str(desc.get("town", "")),
            flatType=str(desc.get("flatType", "")),
            projectId=desc.get("projectId"),
            region=props.get("region"),
            listingType=props.get("listingType"),
            stage=desc.get("stage"),
            ballotQtr=desc.get("ballotQtr"),
        ))
    return normalized


@app.get("/bto_listings", response_model=List[BTOListing])
def get_bto_listings():
    try:
        raw = _load_bto_json()
        return _normalize_bto_items(raw)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load listings: {e}")


# -------------------------------
# Cost estimates endpoint (batch)
# -------------------------------


class BTOSelectionItem(BaseModel):
    town: Optional[str] = None
    flatType: Optional[str] = None
    exerciseDate: Optional[str] = None


class BatchEstimateRequest(BaseModel):
    selections: Dict[str, BTOSelectionItem]


class EstimateResult(BaseModel):
    projectLocation: Optional[str] = None
    flatType: Optional[str] = None
    exerciseDate: Optional[str] = None
    exerciseDateISO: Optional[str] = None
    projectTier: Optional[str] = None
    estimatedPrice: Optional[float] = None
    ciLower: Optional[float] = None
    ciUpper: Optional[float] = None
    sampleSize: Optional[int] = 0
    trend: Optional[str] = None
    methodology: Optional[str] = None


class BatchEstimateResponse(BaseModel):
    results: Dict[str, EstimateResult]


@app.post("/cost_estimates", response_model=BatchEstimateResponse)
def cost_estimates(req: BatchEstimateRequest):
    try:
        # Convert selections into plain dict for the agent
        sel_dict: Dict[str, Dict[str, Any]] = {
            key: {
                "town": (val.town or ""),
                "flatType": (val.flatType or ""),
                "exerciseDate": (val.exerciseDate or "October 2025"),
            }
            for key, val in (req.selections or {}).items()
        }
        results = run_estimates_for_selection(sel_dict)
        # Pydantic will coerce dict of dicts into BatchEstimateResponse
        return BatchEstimateResponse(results=results)
    except FileNotFoundError as e:
        # Likely missing pricing CSV; surface a helpful error
        raise HTTPException(status_code=500, detail=f"Pricing dataset not found: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute estimates: {e}")


# -------------------------------
# Affordability from estimates endpoint
# -------------------------------


class AffordabilityFromEstimatesRequest(BaseModel):
    total_budget: Optional[float] = None
    session_id: Optional[str] = None
    estimates: Dict[str, EstimateResult]


class AffordabilityExplanation(BaseModel):
    affordability_status: str
    shortfall: Optional[float] = None
    margin_vs_estimate: Optional[float] = None
    confidence: Optional[str] = None
    explanation: Optional[str] = None


class AffordabilityFromEstimatesResponse(BaseModel):
    total_budget: float
    results: Dict[str, AffordabilityExplanation]


@app.post("/affordability_from_estimates", response_model=AffordabilityFromEstimatesResponse)
def affordability_from_estimates(req: AffordabilityFromEstimatesRequest):
    # Resolve total budget from request or session store
    budget: Optional[float] = req.total_budget
    if budget is None and req.session_id:
        stored = BUDGET_STORE.get(req.session_id)
        if stored:
            budget = float(stored.get("total_budget", 0.0))
    if budget is None:
        raise HTTPException(status_code=400, detail="Provide total_budget or a valid session_id")

    try:
        # Convert Pydantic EstimateResult objects to plain dicts (Pydantic v1/v2 compatible)
        est_dict: Dict[str, Dict[str, Any]] = {}
        for k, v in req.estimates.items():
            if hasattr(v, "model_dump"):
                est_dict[k] = v.model_dump()
            elif hasattr(v, "dict"):
                est_dict[k] = v.dict()
            else:
                est_dict[k] = v  # already a dict
        assessed = assess_estimates_with_budget(budget, est_dict)
        return AffordabilityFromEstimatesResponse(total_budget=round(budget, 2), results=assessed)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assess affordability: {e}")




#######TRANSPORT EFFICIENCY (MILI)####



# --- Web scraping agent ---
@app.post("/scrape_bto")
async def scrape_bto(url: str):
    """Scrape BTO project data from HDB website and save to bto_data.json."""
    await launch_websearch(
        url=url,
        headless=True,
        verbose=False,
        pretty=True,
        csv_path=None,
        by_name=True,
        coords_only=False,
    )
    return {"status": "scraping completed", "source_url": url}


# --- Single BTO analysis ---
@app.post("/analyze_bto")
def analyze_bto(name: str, postal_code: str, time_period: str):
    result = analyze_bto_transport(name, postal_code, time_period)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

# --- Analyze ALL BTOs ---
@app.post("/analyze_all_btos")
def analyze_all(postal_code: str, time_period: str):
    result = analyze_all_bto_transports(postal_code, time_period)

    # If every single one failed
    if all("error" in r for r in result.values()):
        raise HTTPException(status_code=400, detail="All analyses failed")

    return result


# --- Compare multiple BTOs ---
@app.post("/compare_btos")
def compare_btos(destination_address: str, time_period: str, names: Optional[List[str]] = None):
    """Compare transport accessibility across multiple BTO projects."""
    try:
        result = compare_bto_transports(destination_address, time_period, names)
        return result
    except ValueError as e:
        # Known/expected error (invalid time_period, no data, etc.)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Unexpected error
        raise HTTPException(status_code=500, detail="Internal server error")


# --- Get available BTOs (from scraped data) ---
@app.get("/btos")
def list_btos():
    """List all available BTO projects from bto_data.json."""
    return {"btos": get_bto_locations()}


# --- Clear comparison data ---
@app.delete("/compare_btos/clear")
def clear_comparisons():
    """Clear stored BTO comparison data."""
    clear_comparison_data()
    return {"status": "comparison data cleared"}


# --- Comparison history ---
@app.get("/compare_btos/history")
def comparison_history():
    """List analyzed BTOs available for comparison along with basic metadata."""
    try:
        return {"history": get_comparison_history()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))