from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from bto_transport import (
    get_bto_locations,
    analyze_bto_transport,
    compare_bto_transports,
    clear_comparison_data
)

app = FastAPI(title="BTO Transport API", version="1.0")

# ----------------------------
# Request models
# ----------------------------
class AnalyzeRequest(BaseModel):
    name: str
    postal_code: str
    time_period: str


class CompareRequest(BaseModel):
    destination_address: str
    time_period: str

# ----------------------------
# API endpoints
# ----------------------------
@app.get("/")
def root():
    return {"message": "BTO Transport API is running! Use /docs for the interactive API."}


@app.get("/bto/locations")
def list_bto_locations():
    try:
        return get_bto_locations()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/bto/analyze")
def analyze_bto(req: AnalyzeRequest):
    """
    Analyze transport for a single BTO location by name.
    """
    result = analyze_bto_transport(req.name, req.postal_code, req.time_period)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/bto/compare")
def compare_btos(req: CompareRequest):
    """
    Compare transport accessibility for multiple BTOs to a destination address.
    """
    result = compare_bto_transports(req.destination_address, req.time_period)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.delete("/bto/clear")
def clear_data():
    """
    Clear stored comparison data.
    """
    try:
        clear_comparison_data()
        return {"status": "comparison data cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))