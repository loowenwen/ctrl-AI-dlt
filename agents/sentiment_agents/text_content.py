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

AWS_REGION = "us-east-1"
BEDROCK_MODEL_ID = os.getenv("CLAUDE_35")

session = boto3.Session(region_name="us-east-1")

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
        Include evidence and referenced links (URLS) in your answer. USE LINKS ALWAYS. Label with [URL].
       """
)


text_extract=Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    callback_handler=PrintingCallbackHandler()
)


