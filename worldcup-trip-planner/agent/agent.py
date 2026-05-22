# agent/agent.py
import asyncio
import os
from dotenv import load_dotenv

# 🌟 CRITICAL FIX: Ensure LlmAgent is imported correctly from the ADK framework
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StdioServerParameters
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# Import your custom tools
from agent.tools import master_travel_tool

load_dotenv()

# SYSTEM_PROMPT instructions
SYSTEM_PROMPT = """
You are a World Cup 2026 Fan Trip Planner. 
When a fan provides details, use the 'master_travel_tool' ONCE to get all matches, flights, and visas.
Then, build and present a beautiful, clear itinerary table within their budget.
"""

# Build the agent using the correct imported class name
trip_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="WorldCupTripPlanner",
    instruction=SYSTEM_PROMPT,
    tools=[master_travel_tool],
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
    
    async for event in runner.run_async(
        user_id=clean_id,
        session_id=session.id,
        new_message=structured_content
    ):
        if event.is_final_response():
            return event.content.parts[0].text