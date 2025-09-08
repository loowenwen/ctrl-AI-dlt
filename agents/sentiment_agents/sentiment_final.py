from query_builder import query_agent
from websearch import websearch_agent
from video_ingestion import transcript_understanding
from tiktok_discovery import webscrape_discover
from sentiment_agent import Sentiment
from text_content import text_extract
import os
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from typing import Optional
from botocore.config import Config
from strands import Agent, tool
from strands.handlers.callback_handler import PrintingCallbackHandler
from strands.models.bedrock import BedrockModel
from strands.multiagent import GraphBuilder
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
BEDROCK_MODEL_ID = os.getenv("CLAUDE_35")

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

# Build the graph
builder = GraphBuilder()

builder.add_node(query_agent,"query_agent")
builder.add_node(websearch_agent,"websearch_agent")
builder.add_node(text_extract,"text_extract")
builder.add_node(transcript_understanding,"transcript_understanding")
builder.add_node(webscrape_discover,"webscrape_discover")
builder.add_node(Sentiment,"sentiment")

builder.add_edge("query_agent", "websearch_agent")
builder.add_edge("websearch_agent", "text_extract")
builder.add_edge("websearch_agent", "transcript_understanding")
builder.add_edge("websearch_agent", "webscrape_discover")
builder.add_edge("webscrape_discover", "transcript_understanding")
builder.add_edge("transcript_understanding", "sentiment")
builder.add_edge("text_extract", "sentiment")


graph = builder.build()


# topic={
#         "age": 29,
#         "flat_type": "4-room",
#         "location": "Toa Payoh",
#         "intent": "HDB BTO July 2025 launch sentiment",
#         "focus": ["TikTok", "YouTube", "reviews", "guides", "explainers"],
#         "concerns": ["MRT", "schools", "resale value"],
#         }

# prompt="What are some BTO launches suitable for a broke student? Give me videos"
# result = graph(prompt)

# # Access the results
# print(f"\nStatus: {result.status}")
# print(f"Execution order: {[node.node_id for node in result.execution_order]}")

# print(f"final answer: {result.results["sentiment"].result}")