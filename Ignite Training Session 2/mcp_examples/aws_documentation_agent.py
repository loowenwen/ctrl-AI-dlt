#!/usr/bin/env python

import logging
import os

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

# AWS Documentation MCP Server
stdio_mcp_client = MCPClient(lambda: stdio_client(
    StdioServerParameters(
        command = which('uvx'),
        args = [ 'awslabs.aws-documentation-mcp-server@latest' ],
        env = {
          "FASTMCP_LOG_LEVEL": "ERROR",
          "AWS_DOCUMENTATION_PARTITION": "aws"
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

AWS_DOCS_SYSTEM_PROMPT = """You are an AWS documentation assistant with access to AWS Documentation tools.

Use the available tools to:
- Search AWS documentation for specific topics
- Read AWS documentation pages
- Get recommendations for related AWS documentation

Provide accurate information based on official AWS documentation."""

prompts = [
    "How do I create an S3 bucket?",
    "What can I update my Lambda function code that I've created?",
    "How may I set up VPC flow logging?"
]

def main():
    with stdio_mcp_client:
        tools = stdio_mcp_client.list_tools_sync()
        aws_docs_agent = Agent(
            system_prompt = AWS_DOCS_SYSTEM_PROMPT,
            model = model,
            tools = tools,
            # callback_handler = None
        )

        # Interactive loop
        print('----------------------------')
        print('AWS Documentation Agent Demo')
        print('----------------------------')
        print('\nExample prompts to try:')
        print('\n'.join(['- ' + p for p in prompts]))
        print("\nType 'exit' to quit.\n")

        while True:
            user_input = input("Question: ")

            if user_input.lower() in ["exit", "quit"]:
                break

            print("\nThinking...\n")
            response = aws_docs_agent(user_input)
            print('\n' + '-' * 80 + '\n')

if __name__ == '__main__':
    main()
