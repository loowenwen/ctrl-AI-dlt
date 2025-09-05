import os
import logging
from dotenv import load_dotenv
from botocore.config import Config
import boto3
from strands import Agent, tool
from strands.handlers.callback_handler import PrintingCallbackHandler
from strands.models.bedrock import BedrockModel
from typing import Optional

# -------------------------------
# load environment variables
# -------------------------------
load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN")

AWS_REGION = "us-east-1"
BEDROCK_MODEL_ID = (
    "arn:aws:bedrock:us-east-1:371061166839:inference-profile/us.anthropic.claude-3-5-sonnet-20240620-v1:0"
)

# -------------------------------
# logging setup
# -------------------------------
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# -------------------------------
# bedrock model setup
# -------------------------------
session = boto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    aws_session_token=AWS_SESSION_TOKEN,
    region_name=AWS_REGION,
)

model = BedrockModel(
    model_id=BEDROCK_MODEL_ID,
    max_tokens=64,
    temperature=0,
    boto_client_config=Config(
        read_timeout=120,
        connect_timeout=120,
        retries=dict(max_attempts=3, mode="adaptive"),
    ),
    boto_session=session,
)

# -------------------------------
# strands tool: classify project
# -------------------------------
@tool
def classify_bto_project(project_town: str, project_name: Optional[str] = None) -> str:
    """
    classify a bto project into one of:
    - standard
    - plus
    - prime

    inputs:
    - project_town: town/estate name
    - project_name: project name if available (optional)

    returns:
    - project_type: "Standard", "Plus", or "Prime"
    """
    # prompt for the agent
    prompt = f"Town: {project_town}\n"
    if project_name:
        prompt += f"Project Name: {project_name}\n"
    prompt += "\nClassify this HDB BTO project into exactly one of: Standard, Plus, Prime."

    agent = Agent(
        model=model,
        system_prompt="""
        You are an HDB BTO project classifier. 
        Always classify projects strictly into exactly one category:
        Standard, Plus, or Prime.
        Do not return any explanations or additional text.
        """,
        callback_handler=PrintingCallbackHandler(),
    )
    result = str(agent(prompt)).strip()

    # normalize output to match dataset labels
    result_lower = result.lower()
    if "prime" in result_lower:
        return "Prime"
    if "plus" in result_lower:
        return "Plus"
    return "Standard"
