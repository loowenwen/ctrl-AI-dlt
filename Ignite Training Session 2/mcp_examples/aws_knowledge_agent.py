#!/usr/bin/env python

"""
AWS Knowledge MCP Server
========================

The AWS Knowledge Model Context Protocol (MCP) Server, is a fully managed remote MCP server that surfaces authoritative AWS knowledge in an LLM-compatible format, including documentation, blog posts, What's New announcements, Well-Architected best practices, code samples, and other official AWS content.

AWS Knowledge MCP Server enables clients and foundation models (FMs) that support MCP to ground their responses in trusted AWS context, guidance, and best practices, providing the guidance needed for accurate reasoning and consistent execution, while reducing manual context management. Customers can now focus on business problems instead of searching for information manually.

The server is publicly accessible at no cost and does not require an AWS account. Usage is subject to rate limits. Give your developers and agents access to the most up-to-date AWS information today by configuring your MCP clients to use the AWS Knowledge MCP Server endpoint, and follow the Getting Started guide for setup instructions.

Important Note: Not all MCP clients today support remote servers. Please make sure that your client supports remote MCP servers or that you have a suitable proxy setup to use this server.

Key Features
- Real-time access to AWS documentation, API references, and architectural guidance
- Less local setup compared to client-hosted servers
- Structured access to AWS knowledge for AI agents

AWS Knowledge capabilities
- Best practices: Discover best practices around using AWS APIs and services
- API documentation: Learn about how to call APIs including required and optional parameters and flags
- Getting started: Find out how to quickly get started using AWS services while following best practices
- The latest information: Access the latest announcements about new AWS services and features

Tools
- search_documentation: Search across all AWS documentation
- read_documentation: Retrieve and convert AWS documentation pages to markdown
- recommend: Get content recommendations for AWS documentation pages

Current knowledge sources
- The latest AWS docs
- API references
- What's New posts
- Getting Started information
- Builder Center
- Blog posts
- Architectural references
- Well-Architected guidance

FAQs
1. Should I use the local AWS Documentation MCP Server or the remote AWS Knowledge MCP Server?
   The Knowledge server indexes a variety of information sources in addition to AWS Documentation including What's New Posts, Getting Started Information, guidance from the Builder Center, Blog posts, Architectural references, and Well-Architected guidance. If your MCP client supports remote servers you can easily try the Knowledge MCP server to see if it suits your needs.
2. Do I need network access to use the AWS Knowledge MCP Server?
   Yes, you will need to be able to access the public internet to access the AWS Knowledge MCP Server.
3. Do I need an AWS account?
   No. You can get started with the Knowledge MCP server without an AWS account. The Knowledge MCP is subject to the AWS Site Terms

Announcement: https://aws.amazon.com/about-aws/whats-new/2025/07/aws-knowledge-mcp-server-available-preview/
Github: https://github.com/awslabs/mcp/tree/main/src/aws-knowledge-mcp-server
"""

import argparse
import logging
import os
import sys

from botocore.config import Config
from mcp import stdio_client, StdioServerParameters
from shutil import which
from typing import List

from strands import Agent
from strands.models.bedrock import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from strands.handlers.callback_handler import PrintingCallbackHandler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
logging.getLogger("strands").setLevel(logging.INFO)
logging.getLogger("strands.agent").setLevel(logging.INFO)
logging.getLogger("strands.event_loop").setLevel(logging.INFO)
logging.getLogger("strands.handlers").setLevel(logging.INFO)
logging.getLogger("strands.models").setLevel(logging.INFO)
logging.getLogger("strands.tools").setLevel(logging.INFO)
logging.getLogger("strands.types").setLevel(logging.INFO)

# Configuration with environment variable fallbacks
HOME = os.getenv('HOME')
PWD = os.getenv('PWD', os.getcwd())
BEDROCK_REGION = os.getenv("BEDROCK_REGION", 'us-west-2')
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.amazon.nova-lite-v1:0")
AWS_API_MCP_WORKING_DIR = os.getenv('AWS_API_MCP_WORKING_DIR', os.path.join(PWD, "api_mcp_server"))

# Ensure working directory exists
os.makedirs(AWS_API_MCP_WORKING_DIR, exist_ok=True)

def create_mcp_client(use_npx: bool = False) -> MCPClient:
    """Create an MCP client for the AWS Knowledge MCP Server.
    
    Args:
        use_npx: If True, use npx instead of uvx for the MCP client
        
    Returns:
        MCPClient: Configured MCP client
        
    Raises:
        RuntimeError: If required command is not found
    """
    if use_npx:
        cmd = which('npx')
        if not cmd:
            raise RuntimeError("npx command not found. Please install Node.js and npm.")
        return MCPClient(lambda: stdio_client(
            StdioServerParameters(
                command=cmd,
                args=[
                    'mcp-remote',
                    'https://knowledge-mcp.global.api.aws'
                ]
            )
        ))
    else:
        cmd = which('uvx')
        if not cmd:
            raise RuntimeError("uvx command not found. Please install uvx.")
        return MCPClient(lambda: stdio_client(
            StdioServerParameters(
                command=cmd,
                args=[
                    'mcp-proxy',
                    '--transport',
                    'streamablehttp',
                    'https://knowledge-mcp.global.api.aws'
                ]
            )
        ))

def create_bedrock_model(model_id: str, region: str, temperature: float = 0.1) -> BedrockModel:
    """Create a Bedrock model with appropriate configuration.
    
    Args:
        model_id: The Bedrock model ID to use
        region: AWS region for Bedrock
        temperature: Model temperature (lower is more deterministic)
        
    Returns:
        BedrockModel: Configured Bedrock model
    """
    return BedrockModel(
        model_id=model_id,
        max_tokens=2048,
        boto_client_config=Config(
            region_name=region,
            read_timeout=120,
            connect_timeout=120,
            retries=dict(max_attempts=3, mode="adaptive"),
        ),
        temperature=temperature
    )

AWS_KNOWLEDGE_SYSTEM_PROMPT = """You are an AWS Knowledge assistant with access to AWS documentation and guidance.

Use the available tools to:
- Search AWS documentation and best practices
- Access API references and getting started guides
- Find architectural guidance and Well-Architected best practices
- Stay up to date with AWS announcements and blog posts

Provide accurate AWS knowledge and guidance based on user questions.
"""

prompts = [
    "What are the best practices for securing an S3 bucket?",
    "How do I enable multi-factor authentication for IAM users?",
    "Explain the difference between AWS Lambda and AWS Fargate",
    "What's the recommended architecture for a highly available web application?",
    "Show me recent announcements about Amazon EKS"
]

def run_interactive_session(agent: Agent, example_prompts: List[str]) -> None:
    """Run an interactive session with the AWS Knowledge Agent.
    
    Args:
        agent: The configured Strands Agent
        example_prompts: List of example prompts to show the user
    """
    print('------------------------')
    print('AWS Knowledge Agent Demo')
    print('------------------------')
    print('\nExample prompts to try:')
    print('\n'.join(['- ' + p for p in example_prompts]))
    print("\nType 'exit' to quit.\n")

    while True:
        try:
            user_input = input("Question: ")

            if user_input.lower() in ["exit", "quit"]:
                break

            print("\nThinking...\n")
            response = agent(user_input)
            print('\n' + '-' * 80 + '\n')
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


def main(use_npx: bool = False) -> None:
    """Main entry point for the AWS Knowledge MCP Server demo.
    
    Args:
        use_npx: If True, use npx instead of uvx for the MCP client
        verbose: If True, enable verbose logging
    """
    logging.getLogger("strands").setLevel(logging.DEBUG)
    
    try:
        # Create MCP client
        mcp_client = create_mcp_client(use_npx=use_npx)
        
        # Create Bedrock model
        model = create_bedrock_model(
            model_id=BEDROCK_MODEL_ID,
            region=BEDROCK_REGION
        )
        
        with mcp_client:
            # Get available tools
            tools = mcp_client.list_tools_sync()
            
            # Create agent with callback handler for better visibility
            aws_knowledge_agent = Agent(
                system_prompt = AWS_KNOWLEDGE_SYSTEM_PROMPT,
                model = model,
                tools = tools,
                callback_handler = PrintingCallbackHandler()
            )
            
            # Run interactive session
            run_interactive_session(aws_knowledge_agent, prompts)
            
    except Exception as e:
        logger.error(f"Error initializing AWS Knowledge Agent: {e}")
        sys.exit(1)

def parse_args():
    """Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(description="AWS Knowledge MCP Server Demo")
    parser.add_argument(
        "--npx", 
        action="store_true", 
        help="Use npx instead of uvx for the MCP client"
    )
    parser.add_argument(
        "-v", "--verbose", 
        action="store_true", 
        help="Enable verbose logging"
    )
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    main(use_npx=args.npx)
