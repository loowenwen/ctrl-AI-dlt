#!/usr/bin/env python

import logging
import os
import random

from botocore.config import Config
from mcp import stdio_client, StdioServerParameters
from shutil import which

from strands import Agent
from strands.models.bedrock import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
logging.getLogger("strands").setLevel(logging.INFO)

HOME = os.getenv('HOME')
BEDROCK_REGION = os.getenv("BEDROCK_REGION", 'us-west-2')
BEDROCK_MODEL_ID = "us.amazon.nova-pro-v1:0"

# AWS Cost Explorer MCP Server
stdio_mcp_client = MCPClient(lambda: stdio_client(
    StdioServerParameters(
        command = which('uvx'),
        args = [ 'awslabs.aws-pricing-mcp-server@latest' ],
        env = {
          "FASTMCP_LOG_LEVEL": "ERROR",
          "AWS_PROFILE": "default",
          "AWS_REGION": "us-east-1"
        },
        disabled = False,
        autoApprove = []
    )
))

# Initialize Strands Agent
model = BedrockModel(
    model_id = BEDROCK_MODEL_ID,
    max_tokens = 2048,
    boto_client_config = Config(
        read_timeout = 120,
        connect_timeout = 120,
        retries = dict(max_attempts=3, mode="adaptive"),
    ),
    temperature = 0.1
)

AWS_PRICING_SYSTEM_PROMPT = """You are an AWS pricing assistant with access to AWS Pricing tools.

Use the available tools to:
- Get current AWS service pricing information
- Compare pricing across regions and service tiers
- Find pricing for specific AWS services and configurations

Provide accurate pricing information based on official AWS pricing data."""

prompts = [
    "What is the pricing for EC2 t3.medium instances in us-east-1?",
    "How much does S3 Standard storage cost per GB?",
    "What are the Lambda pricing tiers and costs?"
]

def main():
    with stdio_mcp_client:
        tools = stdio_mcp_client.list_tools_sync()
        aws_pricing_agent = Agent(
            system_prompt = AWS_PRICING_SYSTEM_PROMPT,
            model = model,
            tools = tools,
            # callback_handler = None
        )

        for prompt in prompts:
            print(f'**Prompt**: {prompt}')
            response = aws_pricing_agent(prompt)
            print('\n' + '-' * 80 + '\n')

if __name__ == '__main__':
    main()
