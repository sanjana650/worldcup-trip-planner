# test_mcp.py
import asyncio
from agent.agent import trip_agent 
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

async def main_loop():
    print("⚽ World Cup 2026 Trip Planner Terminal Chat initialized.")
    print("Type 'exit' or 'quit' to end the session.\n")
    
    # 1. Initialize the session framework ONCE outside the user prompt loop
    session_service = InMemorySessionService()
    runner = Runner(
        agent=trip_agent,
        app_name="worldcup-planner",
        session_service=session_service
    )
    
    session = await session_service.create_session(
        app_name="worldcup-planner",
        user_id="terminal_user"
    )
    
    while True:
        user_input = input("You: ")
        if user_input.strip().lower() in ['exit', 'quit']:
            break
            
        print("\n🤖 Agent is planning... ⏳")
        
        # 2. Package and run natively inside the stable context window
        structured_content = types.Content(
            role='user',
            parts=[types.Part.from_text(text=user_input)]
        )
        
        try:
            async for event in runner.run_async(
                user_id="terminal_user",
                session_id=session.id,
                new_message=structured_content
            ):
                if event.is_final_response():
                    print(f"\nAgent:\n{event.content.parts[0].text}\n")
                    print("-" * 40)
        except Exception as e:
            print(f"Error executing step: {e}")

if __name__ == "__main__":
    asyncio.run(main_loop())