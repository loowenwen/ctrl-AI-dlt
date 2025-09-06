from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import json
from typing import List, Dict, Any
from fastapi.middleware.cors import CORSMiddleware

# Import the provided classes and functions
from bto_transport import Config, BTOTransportAnalyzer, get_bto_locations, analyze_bto_transport, compare_bto_transports, clear_comparison_data

app = FastAPI(
    title="BTO Transport Analysis API",
    description="API for analyzing and comparing public transport accessibility for BTO locations in Singapore.",
    version="1.0.0"
)

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request validation
class AnalyzeRequest(BaseModel):
    name: str
    postal_code: str
    time_period: str

class CompareRequest(BaseModel):
    destination_address: str
    time_period: str

# Streaming function to yield JSON chunks
async def stream_json(data: Dict[str, Any]):
    """
    Stream JSON data as chunks to handle large responses.
    """
    # Serialize the data to JSON string
    json_data = json.dumps(data)
    # Yield chunks of the JSON string
    chunk_size = 1024  # Adjust chunk size as needed
    for i in range(0, len(json_data), chunk_size):
        yield json_data[i:i + chunk_size]
        await asyncio.sleep(0.01)  # Simulate async streaming

@app.get("/bto-locations", response_model=List[Dict[str, Any]])
async def list_bto_locations():
    """
    Retrieve all available BTO locations.
    """
    try:
        bto_locations = get_bto_locations()
        return bto_locations
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/analyze")
async def analyze_bto(request: AnalyzeRequest):
    """
    Analyze transport accessibility for a single BTO location.
    Returns a streaming response to handle large AI-generated outputs.
    """
    try:
        result = analyze_bto_transport(
            name=request.name,
            postal_code=request.postal_code,
            time_period=request.time_period
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return StreamingResponse(
            stream_json(result),
            media_type="application/json"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/compare")
async def compare_btos(request: CompareRequest):
    """
    Compare transport accessibility across multiple BTOs.
    Returns a streaming response to handle large comparison data.
    """
    try:
        result = compare_bto_transports(
            destination_address=request.destination_address,
            time_period=request.time_period
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return StreamingResponse(
            stream_json(result),
            media_type="application/json"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.delete("/clear-comparison")
async def clear_comparison():
    """
    Clear stored comparison data.
    """
    try:
        clear_comparison_data()
        return {"message": "Comparison data cleared successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Check the health of the API.
    """
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)