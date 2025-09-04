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

NOVA_PRO_MODEL_ID = os.environ.get("NOVA_MODEL", "amazon.nova-pro-v1:0")
WS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

# Optional: Use an inference profile if on-demand isn't supported
INFERENCE_PROFILE_ARN = os.getenv("NOVA_PRO_INFERENCE_PROFILE_ARN") or os.getenv("NOVA_INFERENCE_PROFILE_ARN")
if INFERENCE_PROFILE_ARN:
    logger.info("Using Bedrock Inference Profile: %s", INFERENCE_PROFILE_ARN)
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
    boto_session=session,
    inference_profile_arn=INFERENCE_PROFILE_ARN if INFERENCE_PROFILE_ARN else None,
)

SYSTEM_PROMPT = """
You are a search query optimizer.
You optimize search queries based on the given parameters. 
Return one compact natural-language query that a person would type into Google,
including key entities and hints for TikTok and YouTube when relevant. No explanations.
""".strip()

query_agent=Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    callback_handler=PrintingCallbackHandler(),
)
logger.info("Query builder agent initialized (region=%s, model=%s)", WS_DEFAULT_REGION, NOVA_PRO_MODEL_ID)

def build_query_prompt_from_params(params: Dict[str, Any]) -> str:
    # Keep it compact and deterministic for the LLM
    blob = json.dumps(params, ensure_ascii=False, separators=(",", ":"))
    lines = [
        "Draft search context (may include metadata lines):",
        blob,
        "Return exactly one query line."
    ]
    return "\n\n".join(lines)


if __name__ == "__main__":
    topic={
            "age": 29,
            "flat_type": "4-room",
            "location": "Toa Payoh",
            "intent": "HDB BTO July 2025 launch sentiment",
            "focus": ["TikTok", "YouTube", "reviews", "guides", "explainers"],
            "concerns": ["MRT", "schools", "resale value"],
        }
    prompt = build_query_prompt_from_params(topic)
    try:
        # strands.Agent supports call syntax; if your version requires .run, switch to query_agent.run(prompt)
        resp = query_agent(prompt)
    except TypeError:
        # Fallback for versions that use .run(...)
        resp = query_agent.run(prompt)
    print("\n[LLM topic]", resp)