from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
import json
from pathlib import Path

# Reuse budget computation helpers
from agents.bto_budget_estimator import compute_total_budget

app = FastAPI()

# Enable CORS so frontend (React) can call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    price: float


class AffordabilityRequest(BaseModel):
    # Either provide total_budget directly or reference a stored session_id
    total_budget: Optional[float] = None
    session_id: Optional[str] = None
    btos: List[BTOItem]


class AffordabilityItem(BaseModel):
    name: str
    price: float
    affordability_status: str
    shortfall: float


class AffordabilityResponse(BaseModel):
    total_budget: float
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

    # Compute affordability per BTO
    results: List[AffordabilityItem] = []
    for b in req.btos:
        if budget >= b.price:
            status = "Affordable"
            shortfall = 0.0
        else:
            shortfall = round(b.price - budget, 2)
            status = f"Shortfall: ${shortfall:,.2f}"
        results.append(AffordabilityItem(
            name=b.name,
            price=b.price,
            affordability_status=status,
            shortfall=shortfall,
        ))

    return AffordabilityResponse(total_budget=round(budget, 2), results=results)


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
