# AgentBTO: Re-Imagining Your Home Buying Decisions with AI
## Group: ctrl-AI-dlt

## Problem Statement
Deciding on a BTO is often overwhelming. Applicants must weigh many factors—location, price, eligibility rules, and long-term considerations—yet information is scattered across multiple sources (websites, forums, Telegram groups, etc.). This makes it difficult for individuals and families to consolidate insights and make confident decisions.

## Why it matters for the Public Good
Current resources are too general and rarely personalised. As a result, many applicants gravitate toward the same projects, lowering their chances of success and prolonging the path to home ownership. With stringent restrictions and limited opportunities to ballot, making an informed and well-matched BTO decision is not only stressful but also critically important for individuals, families, and society at large.

## Our Solution
We designed a **One-Stop Agentic AI** website that helps users **research, evaluate, and calculate** key factors — **affordability, public sentiment, and transport connectivity** — all **tailored to each homebuyer(s)**. This saves time, reduces confusion, and supports smarter BTO decisions.

### Architecture
**Full Architecture**

<img width="1971" height="2336" alt="Agentic drawio (1)" src="https://github.com/user-attachments/assets/8e5b2790-9f76-4421-aa8f-6ef95226447e" />

**Sentiment Agent**

<img width="893" height="591" alt="Screenshot 2025-09-08 at 1 15 54 AM" src="https://github.com/user-attachments/assets/c6b861e7-b92b-47e9-8c67-1724ff424d28" />

**Transport Agent**

<img width="848" height="494" alt="Screenshot 2025-09-08 at 1 16 10 AM" src="https://github.com/user-attachments/assets/0155ea6d-495c-47a9-9619-6fe91ccafdb5" />

**Affordability Agent**

<img width="772" height="524" alt="Screenshot 2025-09-08 at 1 15 37 AM" src="https://github.com/user-attachments/assets/4c552ef9-c410-46a8-837e-4488a9424341" />

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

