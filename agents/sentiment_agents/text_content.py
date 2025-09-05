from __future__ import annotations
from typing import Any, Dict, List, Tuple
import re
import os
import json
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from typing import Optional
from botocore.config import Config
from strands import Agent, tool
from strands.handlers.callback_handler import PrintingCallbackHandler
from strands.models.bedrock import BedrockModel
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

load_dotenv(".env")

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN")  

AWS_REGION = "us-east-1"
BEDROCK_MODEL_ID = "arn:aws:bedrock:us-east-1:371061166839:inference-profile/us.anthropic.claude-3-5-sonnet-20241022-v2:0"

session = boto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    aws_session_token=AWS_SESSION_TOKEN,
    region_name=AWS_REGION
)

model = BedrockModel(
    model_id=BEDROCK_MODEL_ID,
    max_tokens=1024,
    boto_client_config=Config(
        read_timeout=120,
        connect_timeout=120,
        retries=dict(max_attempts=3, mode="adaptive")
    ),
    boto_session=session
)

SYSTEM_PROMPT=(
        """You are a text extractor. Extract ALL text word for word from the websearch agent results. Exclude video evidence.
        Include evidence and referenced links in your answer.
        Rules:
        - Ensure JSON parses without errors; do NOT use code fences.
        - Keep quotes short and verbatim from the text.
        - Calibrate scores: positive≈0.3..1, negative≈-0.3..-1, mixed≈-0.29..0.29.
        NOTE: document may contain SPELLING ERRORS. (e.g Rich is actually Ridge), please fix the spelling errors!"""
)


text_extract=Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    callback_handler=PrintingCallbackHandler()
)


