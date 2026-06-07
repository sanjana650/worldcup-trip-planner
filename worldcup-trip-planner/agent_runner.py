import asyncio
from dotenv import load_dotenv

load_dotenv()

from agent.agent import trip_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


APP_NAME = "worldcup-planner"
USER_ID = "web_user"

session_service = InMemorySessionService()

runner = Runner(
    agent=trip_agent,
    app_name=APP_NAME,
    session_service=session_service
)

session = None


async def get_or_create_session():
    global session

    if session is None:
        session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID
        )

    return session


async def run_worldcup_agent_async(user_message: str) -> str:
    current_session = await get_or_create_session()

    structured_content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_message)]
    )

    final_text = ""

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=current_session.id,
        new_message=structured_content
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                final_text = event.content.parts[0].text

    if not final_text:
        return "I could not generate a response. Please try again."

    return final_text


def run_worldcup_agent(user_message: str) -> str:
    return asyncio.run(run_worldcup_agent_async(user_message))
