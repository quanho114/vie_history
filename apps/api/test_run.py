import asyncio
import traceback
from app.agents.orchestrator import AgentOrchestrator
from app.core.database import async_session
from app.core.context import active_provider_var, groq_key_var, groq_model_var

async def test_query(orchestrator, query: str):
    print(f"\n=========================================\nInvoking orchestrator.answer for '{query}'...")
    try:
        async with async_session() as db:
            result = await orchestrator.answer(
                query=query,
                db=db,
                session_id="test-session-123",
            )
            print("Result Answer:")
            print(result.answer)
            print("Result Mode:", result.mode)
            print("Result Trace:", result.trace)
    except Exception as e:
        print("Exception caught:")
        traceback.print_exc()

async def main():
    # Set context variables to simulate request headers
    active_provider_var.set("groq")
    groq_key_var.set("gsk_placeholder_not_needed_for_greeting")
    groq_model_var.set("llama-3.3-70b-versatile")
    
    orchestrator = AgentOrchestrator()
    await test_query(orchestrator, "chào bạn")
    await test_query(orchestrator, "tóm tắt tài liệu chiến tranh việt nam")

if __name__ == "__main__":
    asyncio.run(main())
