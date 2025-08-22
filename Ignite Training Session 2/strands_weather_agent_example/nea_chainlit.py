#!/usr/bin/env python

# Simple Chainlit + Strands SDK app
# chainlit run nea_chainlit.py -w --port 8081

import chainlit as cl
import logging
import os

from botocore.config import Config

from nea_agent import nea_agent as agent
from strands import Agent
from strands.handlers.callback_handler import PrintingCallbackHandler
from strands.models.bedrock import BedrockModel

# Set up logging
logger = logging.getLogger(__name__)
logging.getLogger("strands").setLevel(logging.INFO)
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()]
)

HOME = os.getenv('HOME')

# Initialize Bedrock
BEDROCK_REGION = os.getenv("BEDROCK_REGION", 'us-west-2')
BEDROCK_MODELS = [
    'us.amazon.nova-micro-v1:0',
    'us.amazon.nova-lite-v1:0',
    'us.amazon.nova-pro-v1:0',
    'us.anthropic.claude-3-5-haiku-20241022-v1:0',
    'us.anthropic.claude-3-5-sonnet-20241022-v2:0',
    'us.anthropic.claude-3-7-sonnet-20250219-v1:0',
    'us.anthropic.claude-sonnet-4-20250514-v1:0',
]
BEDROCK_MODEL_ID = "us.amazon.nova-micro-v1:0"

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

prompts = [
    "What's the current weather in Singapore?",
    "Will it rain tomorrow? Should I bring an umbrella?",
    "How's the weather looking for the weekend?"
]

# Set up Chainlit
@cl.set_starters
async def set_starters():
    """Chat starter suggestions!"""
    starter_prompts = []
    for prompt in prompts:
        starter_prompts.append(
            cl.Starter(
                label = f'{prompt[:80]}...',
                message = f'{prompt}',
            )
        )
    return starter_prompts

@cl.on_chat_start
async def on_chat_start():
    welcome_message = "Welcome to the Chainlit + Strands chat app! How can I help you today?"
    cl.user_session.set(
        "message_history",
        [{"role": "system", "content": welcome_message}],
    )

@cl.on_message
async def on_message(message: cl.Message):
    # Invoke agent
    agent_stream = agent.stream_async(
        message.content
    )

    # Setup message handling
    message_history = cl.user_session.get('message_history')
    message_history.append({"role": "user", "content": message.content})
    msg = cl.Message(content='')

    # Process response stream
    async for event in agent_stream:
        if 'data' in event:
            text_chunk = event["data"]
            print(text_chunk, end="", flush=True)  # Print chunks as they're generated
            await msg.stream_token(text_chunk)     # Output to Chainlit UI
        elif "current_tool_use" in event and event["current_tool_use"].get("name"):
            # Print tool usage information
            tool_use_chunk = f"\n[Tool use delta for: {event['current_tool_use']['name']}]"
            print(tool_use_chunk)
            await msg.stream_token(tool_use_chunk)  

@cl.on_stop
async def on_stop():
    await cl.Message("Manual stop requested. Chainlit has been stopped").send()

if __name__ == "__main__":
    cl.run()
