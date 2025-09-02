from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

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
