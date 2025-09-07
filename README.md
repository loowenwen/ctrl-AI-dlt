# AgentBTO: Re-Imagining Your Home Buying Decisions with AI
## Group: ctrl-AI-dlt

## Problem Statement
Deciding on a BTO is often overwhelming. Applicants must weigh many factors, location, price, eligibility rules, and long-term considerations, yet information is scattered across multiple sources (websites, forums, Telegram groups, etc.). This makes it difficult for individuals and families to consolidate insights and make confident decisions.

## Why It Matters For The Public Good
Current resources are too general and rarely personalised. As a result, many applicants gravitate toward the same projects, lowering their chances of success and prolonging the path to home ownership. With stringent restrictions and limited opportunities to ballot, making an informed and well-matched BTO decision is not only stressful but also critically important for individuals, families, and society at large.

## Our Solution
We designed a **One-Stop Agentic AI** website that helps users **research, evaluate, and calculate** key factors, **affordability, public sentiment, and transport connectivity**, all **tailored to each homebuyer(s)**. This saves time, reduces confusion, and supports smarter BTO decisions.

### Architecture
**Full Architecture**

<img width="1971" height="2336" alt="Agentic drawio (1)" src="https://github.com/user-attachments/assets/8e5b2790-9f76-4421-aa8f-6ef95226447e" />

# Set up

## .env
Create a .env with the following parameters:
```bash
[optional: Add your AWS keys into .env or inside terminal itself]
AWS_PROFILE=[your aws profile]
REGION="us-east-1"
ONEMAP_EMAIL=[Email used for one map]
ONEMAP_PASSWORD=[one map password]
```

## Install & Run
- Python: create a virtualenv and install deps
  - `python -m venv .venv && source .venv/bin/activate`
  - `pip install -r requirements.txt`
- Playwright browsers (needed for web scraping agent)
  - `python -m playwright install`
- AWS credentials for Bedrock
  - Either export a profile (`AWS_PROFILE`) or set explicit keys in `.env`:
    - `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, optional `AWS_SESSION_TOKEN`

Backend (FastAPI)
- Run: `uvicorn backend.main:app --reload`
- Default: listens on `http://127.0.0.1:8000`

Frontend (React/Vite)
- In `frontend/`: `npm install` then `npm run dev`

Data
- Cost estimator uses `data/bto_pricing_detail_cleaned.csv`. Ensure the file exists (already in repo).

---

## Agents Overview 
**Affordability Agent**

<img width="772" height="524" alt="Screenshot 2025-09-08 at 1 15 37 AM" src="https://github.com/user-attachments/assets/4c552ef9-c410-46a8-837e-4488a9424341" />

### BTO Budget Estimator
- File: `agents/bto_budget_estimator.py:1`
- Functions:
  - `max_hdb_loan_from_income(income, annual_rate=0.03, years=25)`
  - `total_hdb_budget(cash_savings, cpf_savings, max_loan, retain_oa_amount=20000.0)`
  - `compute_total_budget(household_income, cash_savings, cpf_savings, annual_rate=0.03, tenure_years=25, retain_oa_amount=20000.0)`
- Example:
  - `from agents.bto_budget_estimator import compute_total_budget`
  - `compute_total_budget(household_income=9000, cash_savings=50000, cpf_savings=120000)`

### BTO Cost Estimator Agent
- File: `agents/bto_cost_estimator_agent.py:1`
- What it does: Classifies project tier (Standard/Plus/Prime) and estimates price (with 95% CI) using historical CSV and regression.
- Interactive CLI:
  - `python agents/bto_cost_estimator_agent.py`
- Programmatic entrypoint used by backend:
  - `from agents.bto_cost_estimator_agent import run_estimates_for_selection`
  - Input shape: `{ id: { town, flatType, exerciseDate } }`
  - Output shape: `{ id: { projectLocation, flatType, exerciseDate, exerciseDateISO, projectTier, estimatedPrice, ciLower, ciUpper, sampleSize, trend, methodology } }`

### BTO Affordability Agent
- File: `agents/bto_affordability_agent.py:1`
- What it does: Combines budget and BTO price to assess affordability. Also evaluates affordability against estimated price + CI from the Cost Estimator.
- Tools/Functions:
  - `estimate_hdb_loan_with_budget(household_income, cash_savings, cpf_savings, bto_price, annual_rate=0.03, tenure_years=25)`
  - `assess_affordability_with_budget(total_budget, bto_price)`
  - `assess_estimates_with_budget(total_budget, estimates_dict)` where `estimates_dict` comes from Cost Estimator output (value fields include `estimatedPrice`, `ciLower`, `ciUpper`).

### BTO Web Search (Scraper)
- File: `agents/bto_launch_websearch_agent.py:1`
- Purpose: Scrapes current BTO locations from HDB site and writes `agents/bto_data.json`.
- Examples:
  - Pretty print (headless):
    - `python agents/bto_launch_websearch_agent.py --headless --pretty`
  - Save CSV:
    - `python agents/bto_launch_websearch_agent.py --headless --csv out.csv`
**Transport Agent**

<img width="848" height="494" alt="Screenshot 2025-09-08 at 1 16 10 AM" src="https://github.com/user-attachments/assets/0155ea6d-495c-47a9-9619-6fe91ccafdb5" />

### Transport Analysis
- File: `agents/bto_transport.py:1`
- What it provides:
  - `get_bto_locations()` reads `agents/bto_data.json`
  - `analyze_bto_transport(name, postal_code, time_period)`
  - `compare_bto_transports(destination_address, time_period)`
  - Stores comparison data in `agents/bto_transport_data_for_comparison.json`
- Requires OneMap credentials in `.env` (`ONEMAP_EMAIL`, `ONEMAP_PASSWORD`).

**Sentiment Agent**

<img width="893" height="591" alt="Screenshot 2025-09-08 at 1 15 54 AM" src="https://github.com/user-attachments/assets/c6b861e7-b92b-47e9-8c67-1724ff424d28" />

### Sentiment Agent
- File: `agents/sentiment_agents/sentiment_final.py:1`
- What it provides:
  - DAG orchestration flow of the subagents:
  - `query refiner`: Refines parameters inserted by user into a search query for google search
  - `websearch agent`: Uses google search api to scrape google for tiktok videos, youtube videos and text content regarding user query
  - `video understanding agent`: Download videos, use openai whisper to transcribe videos then send to claude 3.5 to gather summary of transciption
  - `tiktok discovery page scraper agent`: Scrapes tiktok discovery meta data for video links
  - `text extractor agent`: Extract text content ONLY from websearch results
  - `sentiment agent`: Uses text and video results to calculate a final sentiment regarding the user's parameters as well as present evidence.
- Packaged in lambda for easy calling (no fast api required) and scalability (note: should have packaged EACH subagents into one lambda, but due to a lack of time was unable to do so)
---

## Backend API (used by frontend)
- File: `backend/main.py:1`
- Endpoints:
  - `POST /budget`
    - Body: `{ household_income, cash_savings, cpf_savings, annual_rate?, tenure_years?, retain_oa_amount?, session_id? }`
    - Returns: `{ max_hdb_loan, total_budget, cpf_used_in_budget, retained_oa, session_id }`
  - `POST /affordability`
    - Body: `{ total_budget? , session_id?, btos: [{ name, price }] }`
    - Returns: `{ total_budget, results: [{ name, price, affordability_status, shortfall }] }`
  - `GET /bto_listings`
    - Returns normalized BTO items from `data/oct25_bto.json`
  - `POST /check_eligibility` (demo)

Run locally
- `uvicorn backend.main:app --reload`
- Visit `http://127.0.0.1:8000/docs` for interactive Swagger UI.

---

## Typical Workflow
1) Fetch latest BTO locations (optional)
   - `python agents/bto_launch_websearch_agent.py --headless --pretty`
2) Estimate costs for chosen towns/flat types
   - Use `run_estimates_for_selection` or the interactive CLI
3) Compute budget from income/savings
   - Call `POST /budget` or `compute_total_budget(...)`
4) Check affordability
   - Call `POST /affordability` for explicit prices, or use `assess_estimates_with_budget` for estimator outputs
5) Analyze transport
   - Use `analyze_bto_transport` for each BTO and `compare_bto_transports` to compare

---

## Troubleshooting
- Bedrock throttling: If you see `ThrottlingException`, wait 5–10 minutes and retry. The transport analyzer includes backoff.
- OneMap auth: Ensure `ONEMAP_EMAIL` and `ONEMAP_PASSWORD` are valid.
- Playwright: Run `python -m playwright install` once before scraping.
- CSV not found: Cost estimator expects `data/bto_pricing_detail_cleaned.csv` (included). Update path if using a custom dataset.

---

## Utilities / Tests
- `test_bto_agents_comprehensive.py:1` – Interactive suite that guides through web search, single BTO analysis, comparison, and edge cases.
- `analyze_data_structures.py` and `test_json_structure.py` – Dev utilities for data inspection.
