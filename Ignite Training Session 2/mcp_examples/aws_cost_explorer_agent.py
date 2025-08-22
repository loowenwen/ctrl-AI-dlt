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
BEDROCK_MODEL_ID = "us.amazon.nova-lite-v1:0"

# AWS Cost Explorer MCP Server
stdio_mcp_client = MCPClient(lambda: stdio_client(
    StdioServerParameters(
        command = which('uvx'),
        args = [ 'awslabs.cost-explorer-mcp-server@latest' ],
        env = {
          "FASTMCP_LOG_LEVEL": "ERROR",
          "AWS_PROFILE": "default"
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

AWS_COST_EXPLORER_SYSTEM_PROMPT = """You are an AWS Cost Explorer assistant with access to AWS Cost Explorer tools.

Use the available tools to:
- Query AWS Cost Explorer data and metrics
- Analyze costs across services, regions and time periods 
- Break down costs by tags, instance types and other dimensions
- Generate cost forecasts and predictions

Provide accurate cost analysis based on AWS Cost Explorer data."""

EXAMPLE_PROMPTS = """Show me my AWS costs for the last 3 months grouped by service in us-east-1 region
Break down my S3 costs by storage class for Q1 2025
Show me costs for production resources tagged with Environment=prod
What was my EC2 instance usage by instance type?
Compare my AWS costs between April and May 2025
How did my EC2 costs change from last month to this month?
Why did my AWS bill increase in June compared to May?
What caused the spike in my S3 costs last month?
Forecast my AWS costs for next month
Predict my EC2 spending for the next quarter
What will my total AWS bill be for the rest of 2025?"""
prompts = random.sample(EXAMPLE_PROMPTS.split('\n'), 3)

def main():
    with stdio_mcp_client:
        tools = stdio_mcp_client.list_tools_sync()
        aws_docs_agent = Agent(
            system_prompt = AWS_COST_EXPLORER_SYSTEM_PROMPT,
            model = model,
            tools = tools,
            # callback_handler = None
        )

        for prompt in prompts:
            print(f'**Prompt**: {prompt}')
            response = aws_docs_agent(prompt)
            print('\n' + '-' * 80 + '\n')

if __name__ == '__main__':
    main()
