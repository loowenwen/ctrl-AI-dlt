import prompt
from google.adk.agents import Agent
from google.adk.tools import google_search, url_context
import os
import certifi
from dotenv import load_dotenv
from prompt import SOURCE_IMAGE
from pathlib import Path
import types
from tools import search_and_download_thumbnails
from urllib import response
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
import asyncio
import os
from google.genai import types
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
load_dotenv()



os.environ['SSL_CERT_FILE'] = certifi.where()

Image_sourcer = Agent(
    name="image_sourcer",
    model="gemini-2.5-pro", 
    description="Agent to look for related images ",
    instruction=SOURCE_IMAGE,
    tools=[search_and_download_thumbnails],
    output_key="sourced_images"
)


APP_NAME = "google_search_agent"
USER_ID = "user1234"
SESSION_ID = "1234"


# Session and Runner
async def setup_session_and_runner():
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    runner = Runner(
        agent=Image_sourcer, app_name=APP_NAME, session_service=session_service
    )
    return session, runner


# Agent Interaction
async def call_agent_async(query):
    if not query.strip():
        raise ValueError("Query cannot be empty")

    # 1) Truncate file at the START of the run
    Path("findings.txt").write_text("", encoding="utf-8")

    content = types.Content(role="user", parts=[types.Part(text=query)])
    session, runner = await setup_session_and_runner()
    events = runner.run_async(
        user_id=USER_ID, session_id=SESSION_ID, new_message=content
    )

    try:
        async for event in events:
            if event.is_final_response():
                final_response = event.content.parts[0].text
                print("Agent Response: ", final_response)

                # 2) Append each agent’s final output for THIS run
                with open("findings.txt", "a", encoding="utf-8") as f:
                    f.write(final_response + "\n\n---\n\n")
    except Exception as e:
        print(f"Error during agent execution: {str(e)}")

asyncio.run(call_agent_async("HDB BTO Toa Payoh"))