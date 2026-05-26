# agent/agent.py
from dotenv import load_dotenv

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from agent.prompts import SYSTEM_PROMPT
from agent.tools import flight_estimate_tool, itinerary_tool, master_travel_tool, visa_requirements_tool

load_dotenv()

trip_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="WorldCupTripPlanner",
    instruction=SYSTEM_PROMPT,
    tools=[master_travel_tool, visa_requirements_tool, flight_estimate_tool, itinerary_tool],
)

async def run_agent(user_message: str, session_id: str):
    """
    Directly invokes the ADK Runner workflow with unified session matching.
    """
    session_service = InMemorySessionService()
    runner = Runner(
        agent=trip_agent,
        app_name="worldcup-planner",
        session_service=session_service
    )
    
    clean_id = f"session_{session_id}"
    session = await session_service.create_session(
        app_name="worldcup-planner",
        user_id=clean_id
    )
    
    from google.genai import types
    
    structured_content = types.Content(
        role='user',
        parts=[types.Part.from_text(text=user_message)]
    )
    
    final_text = None

    try:
        async for event in runner.run_async(
            user_id=clean_id,
            session_id=session.id,
            new_message=structured_content
        ):
            if event.is_final_response():
                if not event.content or not event.content.parts:
                    raise RuntimeError("Agent finished without a text response.")

                final_text = event.content.parts[0].text
    except Exception as exc:
        message = str(exc)
        if "API key was reported as leaked" in message:
            raise RuntimeError(
                "Gemini rejected the request because your API key was reported as leaked. "
                "Create a new API key, update your .env file, and revoke the old key."
            ) from exc

        if "PERMISSION_DENIED" in message or "403" in message:
            raise RuntimeError(
                "Gemini rejected the request with a permission error. "
                "Check that your API key is valid, enabled, and present in your .env file."
            ) from exc

        raise

    if final_text:
        return final_text

    raise RuntimeError("Agent did not return a final response.")
