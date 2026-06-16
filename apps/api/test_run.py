import asyncio
import traceback
from app.agents.orchestrator import AgentOrchestrator
from app.core.database import async_session_factory
from app.models.user import User
from app.core.context import active_provider_var, groq_key_var, groq_model_var
from sqlalchemy import select

async def main():
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.email == "admin@historiai.vn")
        )
        user = result.scalar_one_or_none()
        if not user:
            print("User admin@historiai.vn not found!")
            return
        
        settings = user.settings or {}
        groq_key = settings.get("groq_key")
        print("Retrieved key (masked):", groq_key[:10] + "..." if groq_key else "None")

        # Set context variables
        active_provider_var.set("groq")
        groq_key_var.set(groq_key)
        groq_model_var.set("llama-3.3-70b-versatile")

        orchestrator = AgentOrchestrator()
        
        print("\n=========================================\nInvoking orchestrator.answer...")
        try:
            res = await orchestrator.answer(
                query="chiến tranh vn kết thúc ngày nào",
                db=session,
                session_id="test-session-real-key",
            )
            print("Result Answer:")
            print(res.answer)
            print("Result Mode:", res.mode)
            print("Result Trace:", res.trace)
        except Exception as e:
            print("Exception caught:")
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
