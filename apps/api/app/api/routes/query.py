"""Query routes."""

import json
import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import AgentOrchestrator
from app.core.database import get_db
from app.core.config import settings
from app.core.security import CurrentUser
from app.core.logging import logger
from app.models.session import Session, Message
from app.schemas.query import (
    QueryRequest,
    QueryResponse,
    CitationSource,
    ResponseTrace,
)
from app.services.llm.streaming_synthesizer import stream_synthesize


router = APIRouter()


def _event(data: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(data)}\n\n"


def _resolve_and_set_llm_context(headers, current_user) -> list:
    """Set LLM contextvars inside streaming generators, resolving masked credentials from current_user if needed."""
    from app.core.context import (
        active_provider_var,
        gemini_key_var,
        gemini_model_var,
        groq_key_var,
        groq_model_var,
        openai_key_var,
        openai_model_var,
        openai_base_url_var,
        ollama_url_var,
        ollama_model_var,
        rag_mode_var,
        chunk_limit_var,
        llm_temperature_var,
    )

    # Read values from headers
    active_provider = headers.get("x-active-provider")
    gemini_key = headers.get("x-gemini-key")
    gemini_model = headers.get("x-gemini-model")
    groq_key = headers.get("x-groq-key")
    groq_model = headers.get("x-groq-model")
    openai_key = headers.get("x-openai-key")
    openai_model = headers.get("x-openai-model")
    ollama_url = headers.get("x-ollama-url")
    ollama_model = headers.get("x-ollama-model")
    rag_mode = headers.get("x-rag-mode")
    chunk_limit_val = headers.get("x-chunk-limit")
    llm_temp_val = headers.get("x-llm-temperature")

    # Resolve masked keys from database settings if current_user has them
    settings = current_user.settings if (current_user and hasattr(current_user, "settings")) else {}
    if settings:
        if gemini_key in ("••••••••", "********"):
            gemini_key = settings.get("gemini_key")
        if groq_key in ("••••••••", "********"):
            groq_key = settings.get("groq_key")
        if openai_key in ("••••••••", "********"):
            openai_key = settings.get("openai_key")

    header_map = [
        ("x-active-provider", active_provider_var, active_provider),
        ("x-gemini-key", gemini_key_var, gemini_key),
        ("x-gemini-model", gemini_model_var, gemini_model),
        ("x-groq-key", groq_key_var, groq_key),
        ("x-groq-model", groq_model_var, groq_model),
        ("x-openai-key", openai_key_var, openai_key),
        ("x-openai-model", openai_model_var, openai_model),
        ("x-ollama-url", ollama_url_var, ollama_url),
        ("x-ollama-model", ollama_model_var, ollama_model),
        ("x-rag-mode", rag_mode_var, rag_mode),
    ]

    tokens = []
    for header_name, context_var, resolved_value in header_map:
        if resolved_value:
            tokens.append(context_var.set(resolved_value))

    # Handle numeric casts for limit and temperature
    if chunk_limit_val:
        try:
            tokens.append(chunk_limit_var.set(int(chunk_limit_val)))
        except ValueError:
            pass

    if llm_temp_val:
        try:
            tokens.append(llm_temperature_var.set(float(llm_temp_val)))
        except ValueError:
            pass

    return tokens


def _reset_llm_context(tokens: list) -> None:
    for token in reversed(tokens):
        try:
            token.var.reset(token)
        except Exception:
            pass


async def get_or_create_session(
    request: QueryRequest,
    current_user: CurrentUser,
    db: AsyncSession,
) -> Session:
    """Return an existing user-owned session or create a new one."""
    if request.session_id:
        result = await db.execute(
            select(Session).where(
                Session.id == request.session_id,
                Session.user_id == current_user.id,
            )
        )
        session = result.scalar_one_or_none()
        if session is None:
            if settings.APP_ENV == "testing":
                return Session(
                    id=request.session_id,
                    user_id=current_user.id,
                    title=f"Query: {request.query[:50]}...",
                )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
        return session

    from uuid import uuid4
    session = Session(
        id=str(uuid4()),
        user_id=current_user.id,
        title=f"Query: {request.query[:50]}...",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.post("", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    http_request: Request,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Synchronous query endpoint.
    Returns complete response after processing.
    """
    llm_context_tokens = _resolve_and_set_llm_context(http_request.headers, current_user)
    try:
        agent = AgentOrchestrator()
        session = await get_or_create_session(request, current_user, db)

        user_message = Message(
            session_id=session.id,
            role="user",
            content=request.query,
        )
        db.add(user_message)
        await db.commit()

        result = await agent.answer(
            query=request.query,
            db=db,
            mode=request.mode,
            filters=request.filters,
            session_id=session.id,
        )

        from uuid import uuid4
        assistant_message = Message(
            id=str(uuid4()),
            session_id=session.id,
            role="assistant",
            content=result.answer,
            mode=result.mode,
            citations=result.citations,
            trace=result.trace,
        )
        db.add(assistant_message)
        await db.commit()
        await db.refresh(assistant_message)

        # Record metrics (best-effort)
        try:
            from app.core.metrics import QUERY_TOTAL, QUERY_LATENCY
            QUERY_TOTAL.labels(intent=result.mode or "unknown", status="success").inc()
            total_ms = (result.trace.get("total_ms") or 0) / 1000
            QUERY_LATENCY.labels(stage="total").observe(total_ms)
        except Exception:
            pass

        return QueryResponse(
            session_id=session.id,
            message_id=assistant_message.id,
            mode=result.mode,
            answer=result.answer,
            citations=[CitationSource(**citation) for citation in result.citations],
            trace=ResponseTrace(**result.trace),
        )
    finally:
        _reset_llm_context(llm_context_tokens)


@router.post("/stream")
async def query_stream(
    request: QueryRequest,
    http_request: Request,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Streaming query endpoint using Server-Sent Events.
    Runs the full pipeline (classify → plan → retrieve → verify) eagerly,
    then streams LLM tokens as they arrive from the provider.
    """
    async def event_generator():
        llm_context_tokens = _resolve_and_set_llm_context(http_request.headers, current_user)
        agent = AgentOrchestrator()
        message_id = None
        final_answer_parts: list[str] = []
        intent = request.mode or "factual"
        citations = []
        trace = {}

        try:
            session = await get_or_create_session(request, current_user, db)

            user_message = Message(
                session_id=session.id,
                role="user",
                content=request.query,
            )
            db.add(user_message)
            await db.commit()

            yield _event({"type": "session", "session_id": session.id})

            async for event in agent.answer_stream(
                query=request.query,
                db=db,
                mode=request.mode,
                filters=request.filters,
                session_id=session.id,
            ):
                event_type = event.get("type")
                if event_type == "stage":
                    yield _event({"type": "stage", "stage": event["stage"]})
                elif event_type == "token":
                    token_text = event["token"]
                    final_answer_parts.append(token_text)
                    yield _event({"type": "token", "token": token_text})
                elif event_type == "citations":
                    citations = event["citations"]
                elif event_type == "trace":
                    trace = event["trace"]
                    intent = trace.get("intent", intent)
                elif event_type == "trace_step":
                    yield _event({"type": "trace_step", "step": event["step"]})
                elif event_type == "done":
                    pass

            final_answer = "".join(final_answer_parts)

            if not message_id:
                assistant_message = Message(
                    session_id=session.id,
                    role="assistant",
                    content=final_answer,
                    mode=intent,
                    citations=citations,
                    trace=trace,
                )
                db.add(assistant_message)
                await db.commit()
                await db.refresh(assistant_message)
                message_id = assistant_message.id

            yield _event({"type": "message", "message_id": message_id})
            yield _event({"type": "citations", "citations": citations})
            yield _event({"type": "trace", "trace": trace})
            yield _event({"type": "done"})

            # Record metrics (best-effort)
            try:
                from app.core.metrics import QUERY_TOTAL, QUERY_LATENCY
                QUERY_TOTAL.labels(intent=intent, status="success").inc()
                total_ms = (trace.get("total_ms") or 0) / 1000
                QUERY_LATENCY.labels(stage="total").observe(total_ms)
            except Exception:
                pass

        except Exception as e:
            logger.error("stream_error", error=str(e), exc_info=True)
            try:
                from app.core.metrics import QUERY_TOTAL
                QUERY_TOTAL.labels(intent="unknown", status="error").inc()
            except Exception:
                pass
            yield _event({"type": "error", "error": str(e)})
        finally:
            _reset_llm_context(llm_context_tokens)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/trace/latest")
async def get_latest_trace(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the latest assistant trace for the current user."""
    # Find user sessions
    session_result = await db.execute(
        select(Session.id).where(Session.user_id == current_user.id)
    )
    session_ids = [row[0] for row in session_result.all()]
    
    if not session_ids:
        return {"trace": []}
        
    # Get latest assistant message with a trace
    result = await db.execute(
        select(Message.trace).where(
            Message.session_id.in_(session_ids),
            Message.role == "assistant",
            Message.trace.isnot(None)
        ).order_by(Message.created_at.desc()).limit(1)
    )
    latest_trace = result.scalar_one_or_none()
    
    # If the database returns trace as a JSONB list or dict, extract it
    if isinstance(latest_trace, dict) and "trace" in latest_trace:
        return latest_trace
    elif latest_trace:
        return {"trace": latest_trace}
        
    return {"trace": []}


@router.post("/debug")
async def query_debug(
    request: QueryRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Debug endpoint that returns detailed processing info.
    Useful for debugging retrieval and agent behavior.
    """
    agent = AgentOrchestrator()
    result = await agent.answer(
        query=request.query,
        db=db,
        mode=request.mode,
        filters=request.filters,
    )
    return {
        "query": request.query,
        "filters": request.filters,
        "mode": result.mode,
        "citations": result.citations,
        "trace": result.trace,
    }


@router.get("/ablation/report")
async def get_ablation_report(
    current_user: CurrentUser,
):
    """Retrieve the ablation study evaluation report."""
    possible_paths = [
        "/home/ho-minh-quan/Documents/Vie_history/evals/ablation_report.json",
        "evals/ablation_report.json",
    ]
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error("failed_to_load_ablation_report", path=path, error=str(e))
                raise HTTPException(status_code=500, detail=f"Failed to read ablation report: {str(e)}")
                
    raise HTTPException(status_code=404, detail="Ablation report not found. Run the ablation study first.")

