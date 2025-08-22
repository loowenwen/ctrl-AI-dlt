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

# Amazon Location Services MCP Server
stdio_mcp_client = MCPClient(lambda: stdio_client(
    StdioServerParameters(
        command = which('uvx'),
        args = [ 'awslabs.aws-location-mcp-server@latest' ],
        env = {
          "AWS_REGION": BEDROCK_REGION,
          "FASTMCP_LOG_LEVEL": "ERROR"
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

LOCATION_SYSTEM_PROMPT = """You are a location services assistant with access to Amazon Location Services tools.

Use the available tools to:
- Find coordinates for addresses or place names
- Get addresses from latitude/longitude coordinates
- Search for places and locations

Provide clear, accurate location information and coordinates in your responses."""

prompts = [
    "Give me the latitude and longitude for 440 Terry Ave N, Seattle, WA 98109-5210, United States",
    "Please provide the details of Seattle Airport",
    "Provide the address for latitude: 47.62292 and longitude: -122.33676",
    "What's nearby to zip code 98109-5210?",
    "Give me the driving directions from zip code 98109-5210 to the Seattle Airport"
]


def main():
    with stdio_mcp_client:
        tools = stdio_mcp_client.list_tools_sync()
        aws_location_agent = Agent(
            system_prompt = LOCATION_SYSTEM_PROMPT,
            model = model,
            tools = tools,
            # callback_handler = None
        )

        # Interactive loop
        print('-----------------------')
        print('AWS Location Agent Demo')
        print('-----------------------')
        print('\nExample prompts to try:')
        print('\n'.join(['- ' + p for p in prompts]))
        print("\nType 'exit' to quit.\n")

        while True:
            user_input = input("Question: ")

            if user_input.lower() in ["exit", "quit"]:
                break

            print("\nThinking...\n")
            response = aws_location_agent(user_input)
            print('\n' + '-' * 80 + '\n')

if __name__ == '__main__':
    main()
