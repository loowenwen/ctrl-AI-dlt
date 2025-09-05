from __future__ import annotations
from typing import Any, Dict, List, Optional
import json
import os
import logging
from strands import Agent, tool
from strands.handlers.callback_handler import PrintingCallbackHandler
from strands.models.bedrock import BedrockModel
import boto3
from botocore.config import Config
from dotenv import load_dotenv
load_dotenv(".env")

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

NOVA_PRO_MODEL_ID = os.environ.get("CLAUDE_35", "amazon.nova-pro-v1:0")
WS_DEFAULT_REGION = "us-east-1"

logger.info("Bedrock region=%s model_id=%s", WS_DEFAULT_REGION, NOVA_PRO_MODEL_ID)

session = boto3.Session(region_name=WS_DEFAULT_REGION)

# Some BedrockModel versions accept inference_profile_arn; if not, it will be ignored safely
model = BedrockModel(
    model_id=NOVA_PRO_MODEL_ID,
    max_tokens=1024,
    boto_client_config=Config(
        read_timeout=120,
        connect_timeout=120,
        retries=dict(max_attempts=3, mode="adaptive"),
    ),
    boto_session=session
)

SYSTEM_PROMPT = """
You are a search query optimizer. 

If the given query is a set of parameters (e.g age, location ,etc), 
you should optimize and convert it to a search query by turning it into a natural language question.
Return one compact natural-language query that a person would type into Google,
including key entities and hints for TikTok and YouTube when relevant. No explanations.

Else if the given query is a direct prompt, you should return it as is without any modifications.
""".strip()

query_agent=Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    callback_handler=PrintingCallbackHandler(),
)
logger.info("Query builder agent initialized (region=%s, model=%s)", WS_DEFAULT_REGION, NOVA_PRO_MODEL_ID)




# if __name__ == "__main__":
#     topic={
#             "age": 29,
#             "flat_type": "4-room",
#             "location": "Toa Payoh",
#             "intent": "HDB BTO July 2025 launch sentiment",
#             "focus": ["TikTok", "YouTube", "reviews", "guides", "explainers"],
#             "concerns": ["MRT", "schools", "resale value"],
#         }
    
    
#     #from params
#     resp = query_agent(str(topic))

#     #from direct prompt

#     #resp1 = query_agent("What are the reviews, guides, and explainers on TikTok and YouTube about the sentiment for the HDB BTO July 2025 launch of 4-room flats in Toa Payoh, focusing on MRT accessibility, nearby schools, and resale value?")