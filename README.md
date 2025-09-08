# Agent-BTOgether: Re-Imagining Your Home Buying Decisions with AI
Group: **ctrl-AI-dlt**

Agent-BTOgether is a one‑stop, agentic AI application that helps Singapore homebuyers research, evaluate, and decide on HDB BTO projects with confidence. It consolidates affordability, cost estimation, public sentiment, and transport connectivity into a single workflow backed by a FastAPI backend and a React (Vite) frontend.

## Table of Contents
1. Overview
2. Features
3. Architecture
4. Tech Stack
5. Prerequisites
6. Quick Start
7. Configuration
8. Agents
9. API Reference
10. Typical Workflow
11. Data Sources
12. Troubleshooting
13. Testing & Utilities
14. Security & Privacy
15. Roadmap
16. Contributing

## Overview
Deciding on a BTO can be overwhelming. Applicants must weigh location, price, eligibility, sentiment, and long‑term considerations while information is scattered across sources. AgentBTO brings these signals together and tailors them to each household’s profile, saving time and reducing uncertainty.

## Features
- Affordability: Compute max HDB loan and total budget from income, cash, and CPF balances.
- Cost Estimation: Classify project tier (Standard/Plus/Prime) and estimate prices with 95% CI from historical data.
- Transport Analysis: Compare commuting efficiency for candidate BTOs using OneMap routing APIs.
- Sentiment Insights: Aggregate video/text content to summarise public sentiment and evidence.
- API + UI: Typed FastAPI endpoints with a React/Vite frontend for an end‑to‑end experience.

## Architecture
High‑level system architecture

<img width="1971" height="2336" alt="Agentic drawio (1)" src="https://github.com/user-attachments/assets/8e5b2790-9f76-4421-aa8f-6ef95226447e" />

## Tech Stack
- Backend: FastAPI, Pydantic, Uvicorn
- Frontend: React, Vite, TypeScript
- Agents: strands‑agents, AWS Bedrock (Claude 3.5 Sonnet), Playwright
- Data/ML: pandas, scikit‑learn, NumPy
- External APIs: OneMap (routing, geocoding)

## Prerequisites
- Python 3.10+ and Node.js 18+ (recommended)
- AWS account with Bedrock access (Claude 3.5 Sonnet)
- OneMap account credentials
- macOS/Linux/WSL (Windows supported where Playwright and OneMap CLI usage is available)

## Quick Start
1) Create a virtual environment and install Python dependencies
   - `python -m venv .venv && source .venv/bin/activate`
   - `pip install -r requirements.txt`
2) Install Playwright browsers (for the web scraping agent)
   - `python -m playwright install`
3) Configure credentials and app settings (see Configuration)
4) Run the backend
   - `uvicorn backend.main:app --reload`
   - Visit `http://127.0.0.1:8000/docs` for interactive API docs
5) Run the frontend
   - `cd frontend && npm install && npm run dev`

## Configuration
Create a `.env` file at the repo root. You may use an AWS profile or explicit keys.

Minimum settings
```bash
# Option A: Use a local AWS profile (preferred for development)
AWS_PROFILE="your-aws-profile"
REGION="us-east-1"

# Option B: Use explicit AWS credentials (avoid committing these)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_SESSION_TOKEN=

# OneMap API credentials
ONEMAP_EMAIL=
ONEMAP_PASSWORD=
```

Notes
- Do not commit `.env` to version control.
- Bedrock region defaults to `us-east-1` in code; align your credentials accordingly.
- OneMap credentials are required for transport analysis. Refer to this [website](https://www.onemap.gov.sg/apidocs/)

## Agents
Affordability & Budget
- File: `agents/bto_budget_estimator.py`
- Key functions: `max_hdb_loan_from_income`, `total_hdb_budget`, `compute_total_budget`

Cost Estimator
- File: `agents/bto_cost_estimator_agent.py`
- What it does: Classifies project tier (Standard/Plus/Prime) and estimates prices with 95% CI via regression over historical data.
- CLI: `python agents/bto_cost_estimator_agent.py`
- Programmatic: `from agents/bto_cost_estimator_agent import run_estimates_for_selection`

Affordability Assessment
- File: `agents/bto_affordability_agent.py`
- What it does: Combines budget and BTO price (or estimator output + CI) to determine affordability/margins.
- Helpers: `estimate_hdb_loan_with_budget`, `assess_affordability_with_budget`, `assess_estimates_with_budget`

Web Scraper (BTO listings)
- File: `agents/bto_launch_websearch_agent.py`
- Purpose: Scrapes HDB page to derive BTO locations and writes `agents/bto_data.json`.
- Examples:
  - Pretty JSON: `python agents/bto_launch_websearch_agent.py --headless --pretty`
  - CSV output: `python agents/bto_launch_websearch_agent.py --headless --csv out.csv`

Transport Analysis
- File: `agents/bto_transport.py`
- Functions: `get_bto_locations`, `analyze_bto_transport`, `compare_bto_transports`
- Stores comparison data at `agents/bto_transport_data_for_comparison.json`
- Requires: `ONEMAP_EMAIL`, `ONEMAP_PASSWORD` in `.env`

Sentiment Pipeline
- File: `agents/sentiment_agents/sentiment_final.py`
- Sub‑agents: query refiner, websearch, video understanding (Whisper + Claude), TikTok discovery, text extractor, sentiment aggregator
- Packaging: currently deployed as a single Lambda; future work splits sub‑agents into separate Lambdas for scalability

## API Reference
Backend file: `backend/main.py`

- POST `/budget`
  - Body: `{ household_income, cash_savings, cpf_savings, annual_rate?, tenure_years?, retain_oa_amount?, session_id? }`
  - Returns: `{ max_hdb_loan, total_budget, cpf_used_in_budget, retained_oa, session_id }`

- POST `/affordability`
  - Body: `{ total_budget? , session_id?, btos: [{ name, price }] }`
  - Returns: `{ total_budget, results: [{ name, price, affordability_status, shortfall }] }`

- POST `/cost_estimates`
  - Body: `{ selections: { id: { town, flatType, exerciseDate } } }`
  - Returns: `{ results: { id: { projectLocation, flatType, exerciseDate, exerciseDateISO, projectTier, estimatedPrice, ciLower, ciUpper, sampleSize, trend, methodology } } }`

- POST `/affordability_from_estimates`
  - Body: `{ total_budget? , session_id?, estimates: { id: EstimateResult } }`
  - Returns: `{ total_budget, results: { id: { affordability_status, shortfall, margin_vs_estimate, confidence, explanation } } }`

- GET `/bto_listings`
  - Returns: list of normalized BTO items from `data/oct25_bto.json`

- POST `/check_eligibility`
  - Demo endpoint returning a simple eligibility decision

Run locally
- `uvicorn backend.main:app --reload`
- Visit Swagger UI at `http://127.0.0.1:8000/docs`

## Typical Workflow
1) Fetch or refresh BTO locations (optional)
   - `python agents/bto_launch_websearch_agent.py --headless --pretty`
2) Estimate costs for selected towns/flat types
   - CLI or `run_estimates_for_selection`
3) Compute budget
   - `POST /budget` or `compute_total_budget(...)`
4) Check affordability
   - `POST /affordability` or `assess_estimates_with_budget` for estimator outputs
5) Analyze transport for finalists
   - `analyze_bto_transport` per BTO; `compare_bto_transports` to compare

## Data Sources
- Historical pricing: `data/bto_pricing_detail_cleaned.csv` (included)
- Live/scraped BTO coordinates: generated by `agents/bto_launch_websearch_agent.py` into `agents/bto_data.json`
- OneMap routing and geocoding APIs (runtime)

## Troubleshooting
- Bedrock throttling: `ThrottlingException` → wait 5–10 minutes and retry (exponential backoff is built into transport analysis).
- OneMap auth: Verify `ONEMAP_EMAIL` and `ONEMAP_PASSWORD` in `.env`.
- Playwright: Ensure `python -m playwright install` is run before scraping.
- Missing CSV: Cost estimator expects `data/bto_pricing_detail_cleaned.csv`.

## Testing & Utilities
- `test_bto_agents_comprehensive.py` – Interactive suite that guides through web search, single BTO analysis, comparison, and edge cases.
- `analyze_data_structures.py`, `test_json_structure.py` – Developer utilities for data inspection.

## Security & Privacy
- Keep `.env` out of source control. Rotate AWS credentials regularly.
- Scope Bedrock permissions minimally to required models and regions.
- Do not log or persist sensitive user inputs beyond what is necessary for a session.

## Roadmap
- Split sentiment sub‑agents into independent Lambdas for scale and isolation.
- Add caching for cost estimates and transport queries.
- Expand training data and feature engineering for cost regression.
- Add CI checks (lint, type, test) and pre‑commit hooks.