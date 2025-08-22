#!/usr/bin/env python

"""
This is a Strands Telegram Agent example

Warning:
- Some parts of this code (such as the system prompts) may be AI-generated.
- Use of this code is at your own risk

Setup
1. Go to https://web.telegram.org/k/#@BotFather and create a new bot with `/newbot`
   Save the Telegram API token
2. Go to https://t.me/your_bot_name and `/start` the bot
3. Get the Chat ID from the URL below (replacing TELEGRAM_API_TOKEN with your API Key):
   https://api.telegram.org/bot{TELEGRAM_API_TOKEN}/getUpdates

Environment Setup
   export TELEGRAM_API_KEY="..."
   export TELEGRAM_CHAT_ID="..."
"""

import json
import logging
import os
import requests
import urllib.parse

from botocore.config import Config
from strands import Agent, tool
from strands.models.bedrock import BedrockModel


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
logging.getLogger("strands").setLevel(logging.INFO)

# Set up Strands
BEDROCK_MODEL_ID = "us.amazon.nova-lite-v1:0"
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

# Set up Telegram
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TELEGRAM_API_KEY = os.getenv('TELEGRAM_API_KEY')

if not TELEGRAM_API_KEY or not TELEGRAM_CHAT_ID:
    logger.error("TELEGRAM_API_KEY and TELEGRAM_CHAT_ID environment variables must be set.")
    logger.error("See the setup instructions in the file header.")

@tool
def send_telegram_message(message: str, chat_id: str = TELEGRAM_CHAT_ID) -> str:
    """Send a message to a Telegram chat using the Telegram Bot API.
    
    Args:
        message: The message text to send to the Telegram chat
        chat_id: The Telegram Chat ID to send the message to. Defaults to TELEGRAM_CHAT_ID.
        
    Returns:
        JSON string containing the Telegram API response.
    """
    encoded_message = urllib.parse.quote(message)
    url = f'https://api.telegram.org/bot{TELEGRAM_API_KEY}/sendMessage?chat_id={chat_id}&text={encoded_message}'
    response = requests.get(url)
    response = response.json()
    logger.info(response)
    return response

@tool
def telegram_set_webhook(webhook_url: str = ''):
    """Specify a url and receive incoming updates via an outgoing webhook.
    
    Args:
        webhook_url: HTTPS url to send updates to. Use an empty string to remove webhook integration.
        
    Returns:
        JSON string containing the Telegram API response. True on success.
        
    Notes:
        - The url must be HTTPS with a valid certificate (self-signed not allowed)
        - Updates will be sent to this url when they arrive
        - You can set up to 100 simultaneous HTTPS connections to deliver updates quickly

    Reference:
        - https://core.telegram.org/bots/api#setwebhook
    """
    url = f'https://api.telegram.org/bot{TELEGRAM_API_KEY}/setWebhook?url={webhook_url}'
    response = requests.get(url)
    response = response.json()
    logger.info(response)
    return response

@tool
def telegram_get_updates():
    """Get updates from the Telegram Bot API.
    
    Returns:
        JSON string containing the Telegram API response with updates.
        The response includes messages and other updates sent to the bot.
        
    Notes:
        - This method will not work if a webhook is set up
        - Updates are limited to the last 24 hours
        - Long polling is used to get updates efficiently
        
    Reference:
        - https://core.telegram.org/bots/api#getupdates
    """
    url = f'https://api.telegram.org/bot{TELEGRAM_API_KEY}/getUpdates'
    response = requests.get(url)
    response = response.json()
    logger.info(response)
    return response

def main():
    if not TELEGRAM_API_KEY or not TELEGRAM_CHAT_ID:
        logger.error("Cannot run: Missing Telegram credentials")
        return

    print("\nTelegram API Strands Agent\n")
    print("This example demonstrates using Strands Agents to interact with the Telegram API")
    print("You can send messages, set up webhooks, and get updates from your Telegram bot.")
    print("\nExample commands:")
    print("  'send message Hello from the Strands Agent!'")
    print("  'set webhook https://myserver.com/webhook'")
    print("  'remove the webhook URL'")
    print("  'get updates' - Get recent updates from your bot")
    print("  'exit' - Exit the program")

    # Check if credentials are set before running
    if not TELEGRAM_API_KEY or not TELEGRAM_CHAT_ID:
        logger.error("Cannot run: Missing Telegram credentials")
        logger.error("Please set TELEGRAM_API_KEY and TELEGRAM_CHAT_ID environment variables")
        return
        
    # Interactive loop
    while True:
        try:
            user_input = input("\n> ")
            if user_input.lower() in [ "exit", "quit" ]:
                print("\nGoodbye! 👋")
                break

            # Call the Telegram API Strands agent
            response = telegram_agent(user_input)
            logger.info(response)

        except KeyboardInterrupt:
            print("\n\nExecution interrupted. Exiting...")
            break
        except Exception as e:
            print(f"\nAn error occurred: {str(e)}")
            print("Please try a different request.")

telegram_agent = Agent(
    model = model,
    system_prompt = "You are a Telegram bot assistant with access to Telegram API tools. Help users send messages and manage Telegram bot settings.",
    tools = [ send_telegram_message, telegram_set_webhook, telegram_get_updates ]
)

if __name__ == "__main__":
    main()
