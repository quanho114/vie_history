"""LangGraph stateful cyclical multi-agent graph orchestrating supervisor, retrieval, timeline, graph, reasoning, critic, and memory consolidation."""

from __future__ import annotations

import json
from typing import Any, Literal, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from sqlalchemy import select

from app.agents.synthesizer import AnswerSynthesizer
from app.core.database import get_db_context
from app.core.logging import get_logger
from app.models.evolution import KnowledgeDraft
from app.services.graph.neo4j_service import Neo4jService
from app.services.llm.client import get_llm_client
from app.services.llm.json_parser import parse_llm_json
from app.services.retrieval.query_service import QueryService

logger = get_logger("agent_graph")


class AgentState(TypedDict):
    """The persistent state across the multi-agent graph execution."""

    query: str
    session_id: str | None
    filters: dict | None
    # execution_mode: "fast" | "graph" | "agentic" — set by orchestrator via complexity classifier
    execution_mode: str
    plan: list[str]
    current_step: int
    retrieved_chunks: list[dict[str, Any]]
    timeline_events: list[dict[str, Any]]
    graph_entities: list[dict[str, Any]]
    reasoning_steps: list[str]
    critic_feedback: str | None
    replanning_required: bool
    replanning_count: int
    answer: str | None
    citations: list[dict[str, Any]]
    draft_knowledge: list[dict[str, Any]]
    agent_trace: list[dict[str, Any]]
    retrieval_queries: list[str]
    timeline_queries: list[str]
    graph_slugs: list[str]
    world_model_analysis: str | None


# ------------------------------------------------------------------
# Nodes implementation
# ------------------------------------------------------------------


async def supervisor_node(state: AgentState) -> dict[str, Any]:
    """Meta-agent node: understands query, decomposes task, or replans."""
    query = state["query"]
    replanning = state.get("replanning_required", False)
    replanning_count = state.get("replanning_count", 0)
    trace = list(state.get("agent_trace", []))
    plan = state.get("plan", [])

    if plan and not replanning:
        # Returning from sub-agent to supervisor, do not re-plan or overwrite state.
        return {}

    # ── Smart Greeting Detection ──────────────────────────────────
    _GREETING_KEYWORDS = [
        "chào", "hello", "hi", "xin chào", "cảm ơn", "thank", "bye",
        "tạm biệt", "hey", "hola", "good morning", "good evening",
        "chào buổi sáng", "chào buổi tối", "bạn khỏe", "how are you",
        "nice to meet", "rất vui", "giới thiệu", "tên gì", "bạn là ai",
        "what is your name", "who are you",
    ]
    query_lower = query.lower().strip()
    query_clean = query_lower
    for p in ".,!?;:":
        query_clean = query_clean.replace(p, " ")
    words = query_clean.split()
    word_count = len(words)
    
    is_greeting = False
    if word_count <= 15:
        for kw in _GREETING_KEYWORDS:
            if " " in kw:
                if kw in query_lower:
                    is_greeting = True
                    break
            else:
                if kw in words:
                    is_greeting = True
                    break

    if is_greeting and not replanning:
        logger.info("greeting_detected_skipping_pipeline", query=query[:50])
        trace.append({
            "agent": "Supervisor (Greeting Detection)",
            "action": f"Phát hiện câu chào/xã giao: \"{query}\". Bỏ qua pipeline tìm kiếm lịch sử, trả lời trực tiếp.",
            "status": "success",
        })
        return {
            "plan": [],
            "current_step": 0,
            "replanning_required": False,
            "replanning_count": 0,
            "retrieved_chunks": [],
            "timeline_events": [],
            "graph_entities": [],
            "reasoning_steps": [],
            "retrieval_queries": [],
            "timeline_queries": [],
            "graph_slugs": [],
            "agent_trace": trace,
        }

    if replanning:
        # Perform dynamic replanning based on Critic feedback
        feedback = state.get("critic_feedback", "evidence lacks depth")
        logger.info("agentic_replanning_triggered", count=replanning_count, feedback=feedback)

        # Trigger LLM to rewrite queries or extend plan based on critic feedback
        prompt = (
            f"User Query: {query}\n"
            f"Previous Plan: {state.get('plan', [])}\n"
            f"Critic Feedback: {feedback}\n"
            f"Hãy viết lại chiến lược tìm kiếm và các truy vấn con để khắc phục ý kiến phản hồi của Critic.\n"
            f"Trả về kết quả dưới dạng JSON thuần túy có cấu trúc:\n"
            f"{{\n"
            f"  \"retrieval_queries\": [...], # Mảng 1-3 câu truy vấn tìm kiếm văn bản mới tập trung hơn\n"
            f"  \"timeline_queries\": [...],  # Mảng 1-2 từ khóa/năm cụ thể để tra cứu niên biểu mới\n"
            f"  \"graph_slugs\": [...],        # Mảng 1-3 slug thực thể mới cần truy vấn Neo4j\n"
            f"  \"additional_steps\": [\"retrieval_node\", \"graph_node\"] # các node cần chạy lại (ví dụ: ['retrieval_node', 'graph_node'])\n"
            f"}}"
        )

        llm = get_llm_client()
        additional_steps = ["retrieval_node"]
        retrieval_queries = [query]
        timeline_queries = [query]
        graph_slugs = []
        status = "success"
        try:
            resp = await llm.generate(prompt, system="Bạn là Trí tuệ Điều phối Lịch sử (Autonomous History Planner AI).", max_tokens=600)
            if resp.startswith("[Phản hồi từ bộ nhớ tạm"):
                status = "failed"
            parsed = parse_llm_json(resp)
            additional_steps = parsed.get("additional_steps", ["retrieval_node"])
            retrieval_queries = parsed.get("retrieval_queries", [query])
            timeline_queries = parsed.get("timeline_queries", [query])
            graph_slugs = parsed.get("graph_slugs", [])
        except Exception as exc:
            logger.error("agentic_replanning_llm_failed", error=str(exc))
            status = "failed"

        # Append new steps and advance plan
        new_plan = list(state.get("plan", [])) + additional_steps
        trace.append(
            {
                "agent": "Supervisor (Replanning)",
                "action": f"Phân tích phản hồi từ Critic. Tái lập kế hoạch, cấu trúc lại sub-queries:\n"
                          f"- Retrieval: {retrieval_queries}\n"
                          f"- Timeline: {timeline_queries}\n"
                          f"- Graph Slugs: {graph_slugs}" if status == "success" else "Tái lập kế hoạch thất bại do lỗi kết nối LLM.",
                "status": status,
            }
        )

        return {
            "plan": new_plan,
            "replanning_required": False,
            "replanning_count": replanning_count + 1,
            "critic_feedback": None,
            "retrieval_queries": retrieval_queries,
            "timeline_queries": timeline_queries,
            "graph_slugs": graph_slugs,
            "agent_trace": trace,
        }

    # Initial path: build plan based on execution_mode
    mode = state.get("execution_mode", "agentic")
    logger.info("supervisor_planning", mode=mode, query=query[:60])

    retrieval_queries = [query]
    timeline_queries = [query]
    graph_slugs = []

    if mode == "fast":
        # Fast: retrieval only — no LLM planner, no graph, no timeline
        plan = ["retrieval_node"]
        trace.append({
            "agent": "Supervisor (Fast Mode)",
            "action": f"Fast path: chỉ vector retrieval. Query: {query}",
            "status": "success",
        })

    elif mode == "graph":
        # Graph: retrieval + graph + timeline — no LLM planner
        plan = ["retrieval_node", "graph_node", "timeline_node"]
        trace.append({
            "agent": "Supervisor (Graph Mode)",
            "action": f"Graph path: retrieval + graph traversal + timeline. Query: {query}",
            "status": "success",
        })

    else:
        # Agentic: research-grade dynamic planning using QueryAnalyzer and HistoricalPlanner
        logger.info("agentic_task_decomposition_started", query=query[:60])
        status = "success"
        try:
            from app.services.agent.query_analyzer import QueryAnalyzer
            from app.services.agent.planner import HistoricalPlanner, AVAILABLE_TOOLS
            
            analyzer = QueryAnalyzer()
            analysis = await analyzer.analyze(query)
            
            planner = HistoricalPlanner()
            raw_plan = await planner.create_plan(query)
            
            # Map tools to nodes using Tool Registry validation mapping
            plan = [AVAILABLE_TOOLS[task["tool"]] for task in raw_plan.get("tasks", []) if task["tool"] in AVAILABLE_TOOLS]
            
            # Use analysis for query boosting and entity tracking
            graph_slugs = analysis.get("entities", [])
            retrieval_queries = [query] + [e for e in analysis.get("entities", []) if e != query]
            timeline_queries = [query]
            
            logger.info("planner_dynamic_plan_generated", plan=plan, analysis=analysis)
        except Exception as exc:
            logger.error("agentic_planning_failed_defaulting_to_fallback", error=str(exc))
            plan = ["retrieval_node", "graph_node", "timeline_node"]
            status = "failed"

        trace.append({
            "agent": "Supervisor (Agentic Planning)",
            "action": f"Kế hoạch động lập từ QueryAnalyzer & HistoricalPlanner:\n"
                      f"- Plan nodes: {plan}\n"
                      f"- Entities extracted: {graph_slugs}" if status == "success" else "Lập kế hoạch động thất bại, dùng fallback.",
            "status": status,
        })

    return {
        "plan": plan,
        "current_step": 0,
        "replanning_required": False,
        "replanning_count": 0,
        "retrieved_chunks": [],
        "timeline_events": [],
        "graph_entities": [],
        "reasoning_steps": [],
        "retrieval_queries": retrieval_queries,
        "timeline_queries": timeline_queries,
        "graph_slugs": graph_slugs,
        "agent_trace": trace,
    }


async def retrieval_node(state: AgentState) -> dict[str, Any]:
    """Dense & Lexical text search agent."""
    query = state["query"]
    queries = state.get("retrieval_queries") or [query]
    trace = list(state.get("agent_trace", []))
    logger.info("agent_retrieval_node_running", queries=queries)

    status = "success"
    retrieved = []
    try:
        service = QueryService()
        import asyncio
        tasks = [service.hybrid_search(q, top_k=6) for q in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, Exception):
                logger.error("hybrid_search_task_failed", error=str(res))
                status = "failed"
            elif res:
                retrieved.extend(res)
        
        # Deduplicate and cap retrieved chunks by length to prevent exceeding LLM TPM rate limits
        from app.core.context import active_provider_var
        from app.core.config import settings
        provider = active_provider_var.get() or settings.LLM_PROVIDER
        char_limit = 3500 if provider == "groq" else 16000
        logger.info("retrieval_capping_configured", provider=provider, char_limit=char_limit)

        seen = set()
        deduped = []
        total_chars = 0
        for chunk in retrieved:
            # Filter low-relevance documents (relevance threshold < 15%)
            # Only apply if cross-encoder score is present and valid, since RRF/lexical scores are on a different scale
            ce_score = chunk.get("cross_encoder_score", 0.0)
            if ce_score > 0.0 and ce_score < 0.15:
                continue
            key = str(chunk.get("chunk_id") or chunk.get("id") or chunk.get("content", "")[:120])
            if key not in seen:
                seen.add(key)
                content = chunk.get("content", "")
                available_chars = char_limit - total_chars
                if available_chars <= 0:
                    break
                if len(content) > available_chars:
                    # If this is the first chunk or we have enough space (>= 200 chars), truncate it
                    if not deduped or available_chars >= 200:
                        chunk_copy = dict(chunk)
                        chunk_copy["content"] = content[:available_chars] + "... [nội dung bị cắt giảm để tránh quá tải]"
                        deduped.append(chunk_copy)
                        total_chars += len(chunk_copy["content"])
                    break
                else:
                    deduped.append(chunk)
                    total_chars += len(content)
        retrieved = deduped
    except Exception as exc:
        logger.error("agent_retrieval_failed", error=str(exc))
        status = "failed"

    trace.append(
        {
            "agent": "Retrieval Agent",
            "action": f"Tìm kiếm văn bản song song hoàn tất. Thu thập {len(retrieved)} phân đoạn văn bản phù hợp." if status == "success" else "Lỗi tìm kiếm cơ sở dữ liệu phân đoạn văn bản.",
            "status": status,
        }
    )

    return {
        "retrieved_chunks": retrieved,
        "current_step": state["current_step"] + 1,
        "agent_trace": trace,
    }


async def timeline_node(state: AgentState) -> dict[str, Any]:
    """Temporal and chronology alignment agent."""
    query = state["query"]
    queries = state.get("timeline_queries") or [query]
    trace = list(state.get("agent_trace", []))
    logger.info("agent_timeline_node_running", queries=queries)

    events = []
    try:
        from app.services.timeline.timeline_service import TimelineService  # noqa: PLC0415
        timeline_svc = TimelineService()
        async with get_db_context() as db:
            for q in queries:
                matching, _ = await timeline_svc.get_events(db, search=q, page_size=6)
                for ev in matching:
                    events.append(
                        {
                            "title": ev.title,
                            "year": ev.year,
                            "month": ev.month,
                            "day": ev.day,
                            "description": ev.description,
                        }
                    )
            
            # Deduplicate events by title
            seen = set()
            deduped = []
            for ev in events:
                if ev["title"] not in seen:
                    seen.add(ev["title"])
                    deduped.append(ev)
            events = deduped
    except Exception as exc:
        logger.error("agent_timeline_failed", error=str(exc))

    trace.append(
        {
            "agent": "Timeline Agent",
            "action": f"Tra cứu niên biểu hoàn tất. Tìm thấy {len(events)} sự kiện mốc thời gian phù hợp.",
            "status": "success",
        }
    )

    return {
        "timeline_events": events,
        "current_step": state["current_step"] + 1,
        "agent_trace": trace,
    }


async def graph_node(state: AgentState) -> dict[str, Any]:
    """Entity relationship graph traversal agent using Neo4j with GraphReasoner fallback."""
    query = state["query"]
    slugs = state.get("graph_slugs") or []
    trace = list(state.get("agent_trace", []))
    logger.info("agent_graph_node_running", slugs=slugs)

    # Fallback if slugs are completely empty
    if not slugs:
        terms = [t.strip() for t in query.split() if len(t.strip()) > 3]
        slugs = [term.lower().replace(",", "").replace(".", "") for term in terms[:3]]

    entities = []
    neo4j_success = False
    action_msg = ""
    try:
        neo4j_svc = Neo4jService()
        connected = await neo4j_svc.check_connection()
        if connected:
            for slug in slugs:
                try:
                    res = await neo4j_svc.get_neighbors(slug, depth=1)
                    if res and res.get("neighbors"):
                        entities.extend(res["neighbors"])
                except Exception:
                    continue
            
            # Deduplicate neighbors by node_slug
            seen = set()
            deduped = []
            for ent in entities:
                if ent.get("node_slug") not in seen:
                    seen.add(ent.get("node_slug"))
                    deduped.append(ent)
            entities = deduped
            neo4j_success = True
            action_msg = f"Duyệt đồ thị Neo4j hoàn tất. Tìm được {len(entities)} quan hệ thực thể lân cận."
    except Exception as exc:
        logger.warning("neo4j_service_failed_falling_back_to_postgres", error=str(exc))

    if not neo4j_success:
        logger.info("falling_back_to_graph_reasoner_networkx")
        from app.services.graph.graph_reasoner import GraphReasoner
        reasoner = GraphReasoner()
        try:
            async with get_db_context() as db:
                for slug in slugs:
                    try:
                        res = await reasoner.get_neighbors(db, slug, depth=1)
                        if res and res.get("neighbors"):
                            entities.extend(res["neighbors"])
                    except Exception as e:
                        logger.warning("graph_reasoner_fallback_failed_for_slug", slug=slug, error=str(e))
                        continue
                
                # Deduplicate neighbors by node_slug
                seen = set()
                deduped = []
                for ent in entities:
                    if ent.get("node_slug") not in seen:
                        seen.add(ent.get("node_slug"))
                        deduped.append(ent)
                entities = deduped
                action_msg = f"Neo4j offline. Đã kích hoạt cơ chế dự phòng NetworkX. Khôi phục thành công {len(entities)} quan hệ thực thể từ PostgreSQL."
        except Exception as exc:
            logger.error("graph_reasoner_fallback_failed", error=str(exc))
            action_msg = "Không thể duyệt đồ thị (cả Neo4j và dự phòng NetworkX đều gặp lỗi)."

    trace.append(
        {
            "agent": "Graph Agent",
            "action": action_msg,
            "status": "success" if entities else "warning",
        }
    )

    return {
        "graph_entities": entities,
        "current_step": state["current_step"] + 1,
        "agent_trace": trace,
    }



async def world_model_node(state: AgentState) -> dict[str, Any]:
    """World Model agent: analyzes deep causal connections and historical forces."""
    query = state["query"]
    trace = list(state.get("agent_trace", []))
    logger.info("agent_world_model_node_running", query=query[:50])

    # Assemble context for World Model to analyze
    context_blocks = []
    for chunk in state.get("retrieved_chunks", []):
        context_blocks.append(f" VĂN BẢN: {chunk.get('content', '')}")
    for ev in state.get("timeline_events", []):
        context_blocks.append(f" NIÊN BIỂU: {ev['title']} ({ev['year']}) - {ev['description']}")
    for ent in state.get("graph_entities", []):
        context_blocks.append(f" QUAN HỆ ĐỒ THỊ: {ent['node_name']} ({ent['edge_type']}) - {ent.get('direction', '')}")

    context = "\n".join(context_blocks[:15])

    prompt = (
        f"Bạn là World Model Agent của hệ thống Trí tuệ Nhân tạo Lịch sử Việt Nam.\n"
        f"Câu hỏi nghiên cứu: {query}\n\n"
        f"Dữ liệu bối cảnh thô thu thập được:\n{context}\n\n"
        f"Nhiệm vụ của bạn:\n"
        f"Hãy phân tích và mô hình hóa các ĐỘNG LỰC LỊCH SỬ và LIÊN KẾT NHÂN QUẢ vĩ mô ẩn sau câu hỏi này.\n"
        f"Giải thích ảnh hưởng của bối cảnh thời đại, tương quan lực lượng, lý do sâu xa dẫn đến diễn biến lịch sử đó (bằng tiếng Việt).\n"
        f"Hãy trả về phân tích sâu sắc dưới dạng Chain-of-Thought (từng bước lập luận nhân quả). Không viết câu trả lời hoàn chỉnh cho người dùng."
    )

    world_model_analysis = "Không thể sinh phân tích nhân quả lịch sử vĩ mô."
    status = "success"
    try:
        llm = get_llm_client()
        world_model_analysis = await llm.generate(
            prompt,
            system="Bạn là mô hình nhận thức phân tích các lực đẩy lịch sử và động lực nhân quả vĩ mô (World Causal Model).",
            max_tokens=1024
        )
        if world_model_analysis.startswith("[Phản hồi từ bộ nhớ tạm"):
            status = "failed"
    except Exception as exc:
        logger.error("agent_world_model_failed", error=str(exc))
        status = "failed"

    trace.append(
        {
            "agent": "World Model Agent",
            "action": "Phân tích và mô hình hóa liên kết nhân quả lịch sử vĩ mô (Historical Causal Dynamics & World Model Blueprint) thành công." if status == "success" else "Lỗi sinh phân tích nhân quả lịch sử vĩ mô do gián đoạn LLM.",
            "status": status,
        }
    )

    return {
        "world_model_analysis": world_model_analysis,
        "agent_trace": trace,
    }


async def reasoning_node(state: AgentState) -> dict[str, Any]:
    """Synthesizer agent: compiles raw text, graph, and timeline context into grounded response."""
    query = state["query"]
    trace = list(state.get("agent_trace", []))
    logger.info("agent_reasoning_node_running", query=query[:50])

    # Format synthesized context
    context_blocks = []
    for idx, chunk in enumerate(state.get("retrieved_chunks", []), 1):
        context_blocks.append(f" [Nguồn {idx}] VĂN BẢN: {chunk.get('content', '')} (Nguồn: {chunk.get('source_url', 'Wiki')})")

    for ev in state.get("timeline_events", []):
        date_str = f"{ev['year']}-{ev.get('month', 1)}-{ev.get('day', 1)}"
        context_blocks.append(f" NIÊN BIỂU [{date_str}]: {ev['title']} - {ev['description']}")

    for ent in state.get("graph_entities", []):
        dir_str = "->" if ent["direction"] == "outgoing" else "<-"
        context_blocks.append(f" ĐỒ THỊ QUAN HỆ: {state['query']} {dir_str} {ent['node_name']} ({ent['edge_type']})")

    context = "\n".join(context_blocks[:20])

    # Adaptive token budget by execution mode (budget-aware agentic)
    from app.agents.complexity_classifier import TOKEN_BUDGET
    mode = state.get("execution_mode", "agentic")
    max_tokens = TOKEN_BUDGET.get(mode, 1500)

    # Run answer synthesis
    answer_text = ""
    citations = []
    status = "success"

    try:
        llm = get_llm_client()

        # Lightweight path for greetings / no-context queries
        if not context_blocks:
            has_retrieval_runs = bool(state.get("retrieval_queries")) or len(state.get("plan", [])) > 0
            if not has_retrieval_runs:
                prompt = (
                    f"Người dùng nói: \"{query}\"\n\n"
                    f"Đây là câu chào hỏi hoặc câu hỏi xã giao không liên quan đến lịch sử cụ thể.\n"
                    f"Hãy trả lời thân thiện, ngắn gọn (2-3 câu), giới thiệu bản thân là HistoriAI — "
                    f"trợ lý nghiên cứu lịch sử Việt Nam giai đoạn 1945–1975. "
                    f"Mời người dùng đặt câu hỏi lịch sử."
                )
                answer_text = await llm.generate(prompt, system="Bạn là HistoriAI, trợ lý nghiên cứu lịch sử Việt Nam thân thiện.", max_tokens=300)
            else:
                prompt = (
                    f"Người dùng hỏi về lịch sử Việt Nam: \"{query}\"\n\n"
                    f"Hiện tại trong cơ sở dữ liệu (chỉ gồm các tài liệu đã nạp) chưa tìm thấy thông tin phù hợp nào để trả lời câu hỏi này.\n"
                    f"Hãy trả lời người dùng một cách lịch sự, giải thích rõ rằng hệ thống chưa tìm thấy tài liệu liên quan trong cơ sở dữ liệu "
                    f"để trả lời chính xác, và gợi ý họ có thể nạp thêm tài liệu lịch sử ở phần 'Kho tài liệu' hoặc đặt câu hỏi khác."
                )
                answer_text = await llm.generate(prompt, system="Bạn là HistoriAI, trợ lý nghiên cứu lịch sử Việt Nam.", max_tokens=300)
        else:
            world_model_context = ""
            if state.get("world_model_analysis"):
                world_model_context = f"\nBẢN ĐỒ NHÂN QUẢ LỊCH SỬ (WORLD CAUSAL MODEL):\n{state['world_model_analysis']}\n\n"

            query_lower = query.lower()
            if any(k in query_lower for k in ["so sánh", "khác nhau", "giống nhau", "đối chiếu", "phân biệt", " vs ", "versus"]):
                template_instruction = (
                    "HƯỚNG DẪN TRÌNH BÀY (So sánh/Đối chiếu):\n"
                    "- Ở đầu câu trả lời, bắt đầu bằng một blockquote tóm tắt ngắn gọn: `> **Tóm tắt:** [Tóm tắt ngắn gọn 1-2 câu chứa nhận xét so sánh cốt lõi].`\n"
                    "- Bắt buộc sử dụng bảng Markdown để so sánh giữa các đối tượng theo các tiêu chí rõ ràng (ví dụ: Tiêu chí, Đối tượng A, Đối tượng B).\n"
                    "- Nêu tóm tắt điểm tương đồng và khác biệt chính dưới dạng gạch đầu dòng.\n"
                    "- Nêu rõ mục '## Đánh giá / Ý nghĩa lịch sử'.\n"
                    "- Kết thúc bằng phần takeaways: `### Điểm cần ghi nhớ` chứa 2-3 gạch đầu dòng tóm tắt thông điệp quan trọng nhất."
                )
            elif any(k in query_lower for k in ["tiểu sử", "ai là", "thân thế", "sự nghiệp", "cuộc đời", "đóng góp", "vai trò của", "tướng", "lãnh đạo", "nhân vật"]):
                template_instruction = (
                    "HƯỚNG DẪN TRÌNH BÀY (Nhân vật lịch sử):\n"
                    "- Ở đầu câu trả lời, bắt đầu bằng một blockquote tóm tắt ngắn gọn: `> **Tóm tắt:** [Tóm tắt ngắn gọn 1-2 câu về vai trò lớn nhất của nhân vật và thời kỳ hoạt động].`\n"
                    "- Hãy chia thành các mục rõ ràng sau:\n"
                    "  ## Tiểu sử & Thân thế\n"
                    "  ## Vai trò & Đóng góp lịch sử (Liệt kê các mốc hoạt động dạng gạch đầu dòng, sử dụng `- **[Thời gian]:**` nếu có niên biểu)\n"
                    "  ## Đánh giá lịch sử\n"
                    "- Kết thúc bằng phần takeaways: `### Điểm cần ghi nhớ` chứa 2-3 gạch đầu dòng tóm tắt thông điệp quan trọng nhất."
                )
            elif any(k in query_lower for k in ["niên biểu", "diễn biến", "tiến trình", "quá trình", "lịch trình", "mốc thời gian", "ngày", "năm", "khi nào"]):
                template_instruction = (
                    "HƯỚNG DẪN TRÌNH BÀY (Niên biểu/Diễn biến):\n"
                    "- Ở đầu câu trả lời, bắt đầu bằng một blockquote tóm tắt ngắn gọn: `> **Tóm tắt:** [Tóm tắt ngắn gọn 1-2 câu chứa mốc thời gian cốt lõi và kết quả của tiến trình].`\n"
                    "- Trình diễn biến theo trình tự thời gian dưới dạng danh sách gạch đầu dòng thoáng đãng, mỗi sự kiện cách nhau một dòng trống.\n"
                    "- Sử dụng định dạng: `- **[Ngày/Tháng/Năm hoặc Thời gian]:** [Mô tả ngắn gọn sự kiện diễn ra].`\n"
                    "- Chia câu trả lời thành:\n"
                    "  ## Bối cảnh lịch sử\n"
                    "  ## Diễn biến cột mốc\n"
                    "  ## Kết quả & Ý nghĩa lịch sử\n"
                    "- Kết thúc bằng phần takeaways: `### Điểm cần ghi nhớ` chứa 2-3 gạch đầu dòng tóm tắt thông điệp quan trọng nhất."
                )
            else:
                template_instruction = (
                    "HƯỚNG DẪN TRÌNH BÀY (Sự kiện/Khái niệm):\n"
                    "- Ở đầu câu trả lời, bắt đầu bằng một blockquote tóm tắt ngắn gọn: `> **Tóm tắt:** [Tóm tắt ngắn gọn 1-2 câu chứa bối cảnh lớn và kết quả cốt lõi của sự kiện].`\n"
                    "- Chia câu trả lời thành:\n"
                    "  ## Bối cảnh & Nguyên nhân\n"
                    "  ## Diễn biến chính (Nếu có từ 3 mốc thời gian trở lên, bắt buộc liệt kê dạng: `- **[Thời gian]:** [Sự kiện].` cách nhau một dòng trống)\n"
                    "  ## Kết quả & Ý nghĩa lịch sử\n"
                    "- Kết thúc bằng phần takeaways: `### Điểm cần ghi nhớ` chứa 2-3 gạch đầu dòng tóm tắt thông điệp quan trọng nhất."
                )

            system_prompt = (
                "Bạn là HistoriAI, trợ lý nghiên cứu Lịch sử Việt Nam thông minh, chuyên nghiệp và có tư duy trình bày xuất sắc như Claude.\n\n"
                "Nhiệm vụ của bạn là tổng hợp câu trả lời dựa trên dữ liệu nghiên cứu được cung cấp.\n\n"
                "QUY TẮC TRÌNH BÀY (UX/UI & Readability):\n"
                "1. BẮT ĐẦU BẰNG TÓM TẮT CÔ ĐỌNG:\n"
                "   - Luôn bắt đầu bằng khối tóm tắt dạng blockquote (`> **Tóm tắt:** ...`).\n"
                "   - Tóm tắt phải cực kỳ ngắn gọn, CHỈ 1-2 CÂU (tối đa 40 từ), cô đọng giá trị cốt lõi nhất.\n"
                "2. BỐ CỤC PHÂN PHẲNG RÕ RÀNG (Hierarchy):\n"
                "   - Phân chia câu trả lời thành các phần rõ ràng sử dụng tiêu đề cấp 2 (##).\n"
                "   - Tránh hiện tượng 'bức tường chữ'. Các đoạn văn không viết dài quá 3 dòng.\n"
                "3. NHẤN NHÁ TRỰC QUAN CỰC KỲ CHỌN LỌC (Selective Formatting):\n"
                "   - Chỉ in đậm (`**từ khóa**`) cho các thực thể hoặc sự kiện quan trọng nhất (tổng cộng tối đa 5-8 cụm từ cho toàn bài). Tránh lạm dụng gây nhiễu thị giác.\n"
                "   - Trình bày diễn biến/niên biểu bắt buộc dùng gạch đầu dòng dạng: `- **[Thời gian]:** [Mô tả].` cách nhau một dòng trống để dễ quét đọc.\n"
                "4. TRÁNH DẪN DÒNG (Conciseness):\n"
                "   - Đi thẳng vào nội dung câu trả lời. Tuyệt đối KHÔNG viết các câu xã giao, dẫn nhập dài dòng (ví dụ: 'Dưới đây là...', 'Để hiểu rõ...').\n"
                "5. TUYỆT ĐỐI KHÔNG SỬ DỤNG EMOJI:\n"
                "   - Không được sử dụng bất kỳ biểu tượng emoji nào (ví dụ: 📅, 📌, 📚, 🗓️, 🎯) trong toàn bộ câu trả lời để giữ văn phong nghiên cứu học thuật nghiêm túc.\n"
                "6. MỤC TÓM TẮT ĐIỂM GHI NHỚ Ở CUỐI:\n"
                "   - Phải kết thúc bằng tiêu đề cấp 3: `### Điểm cần ghi nhớ` chứa 2-3 gạch đầu dòng cô đọng nhất.\n"
                "7. DẪN NGUỒN TRONG VĂN BẢN (In-text citations):\n"
                "   - Mỗi khi trích dẫn hoặc sử dụng thông tin từ [Nguồn 1], [Nguồn 2], [Nguồn 3], [Nguồn 4], bắt buộc kết thúc câu hoặc ý đó bằng ký hiệu tương ứng dạng [1], [2], [3], [4].\n"
                "   - Ví dụ: 'Ngày 3/2/1994, Hoa Kỳ chính thức gỡ bỏ cấm vận thương mại đối với Việt Nam [2].'\n"
                "   - Tuyệt đối không tự bịa đặt các số nguồn lớn hơn số lượng nguồn được cung cấp."
            )

            prompt = (
                f"Câu hỏi nghiên cứu: {query}\n\n"
                f"{world_model_context}"
                f"Dữ liệu bối cảnh nghiên cứu thu thập được:\n{context}\n\n"
                f"{template_instruction}\n\n"
                f"Hãy biên soạn câu trả lời hoàn thiện đáp ứng đúng quy tắc trình bày và hướng dẫn cụ thể trên."
            )
            answer_text = await llm.generate(prompt, system=system_prompt, max_tokens=max_tokens)
        
        if answer_text.startswith("[Phản hồi từ bộ nhớ tạm"):
            status = "failed"

        # Extract citations
        # Extract citations matching the frontend Citation interface
        citations = [
            {
                "document_id": chunk.get("document_id", ""),
                "document_title": "Wikipedia" if chunk.get("document_title", "Unknown") == "Unknown" else chunk.get("document_title", "Wikipedia"),
                "source_url": chunk.get("source_url", ""),
                "chunk_id": chunk.get("chunk_id", ""),
                "section_title": chunk.get("section_title", ""),
                "excerpt": str(chunk.get("content") or "")[:120] + "...",
                "score": chunk.get("score", chunk.get("rerank_score", 0.9))
            }
            for chunk in state.get("retrieved_chunks", [])[:4]
        ]
    except Exception as exc:
        logger.error("agent_reasoning_synthesis_failed", error=str(exc))
        answer_text = "Không thể tổng hợp câu trả lời do lỗi kỹ thuật."
        status = "failed"

    # ── Post-process: strip stray CJK characters from LLM output ──────
    try:
        from app.services.ingestion.cleaner import ContentCleaner
        _cleaner = ContentCleaner(min_content_length=0)
        answer_text = _cleaner.remove_cjk_characters(answer_text)
    except Exception:
        pass  # Non-critical: never break answer delivery

    trace.append(
        {
            "agent": "Reasoning Agent",
            "action": "Generated final comprehensive response combining chronological sequences and causal graph paths." if status == "success" else "Lỗi kết nối mô hình ngôn ngữ lớn (LLM) khi tổng hợp câu trả lời.",
            "status": status,
        }
    )

    return {
        "answer": answer_text,
        "citations": citations,
        "agent_trace": trace,
    }


async def critic_node(state: AgentState) -> dict[str, Any]:
    """Critic agent: self-reflection, verifies references, claims logic, triggers replanning."""
    query = state["query"]
    answer = state.get("answer", "")
    replanning_count = state.get("replanning_count", 0)
    trace = list(state.get("agent_trace", []))

    logger.info("agent_critic_node_running", query=query[:50])

    # ── Evidence Confidence Gate (Early Stop) ─────────────────────
    # If retrieval evidence is strong, skip LLM critique entirely
    chunks = state.get("retrieved_chunks", [])
    timeline_events = state.get("timeline_events", [])
    citations = state.get("citations", [])
    evidence_count = len(chunks) + len(timeline_events)
    has_grounding = len(citations) > 0 or len(chunks) == 0

    # Strong evidence consensus: vector + timeline both returned results
    if evidence_count >= 4 and has_grounding and replanning_count == 0:
        logger.info("critic_early_stop", evidence_count=evidence_count, reason="high_evidence_consensus")
        trace.append({
            "agent": "Critic Agent (Early Stop)",
            "action": f"Bằng chứng đủ mạnh ({evidence_count} nguồn). Bỏ qua phản tư — chất lượng câu trả lời đã đảm bảo.",
            "status": "success",
        })
        return {"replanning_required": False, "critic_feedback": None, "agent_trace": trace}

    prompt = (
        f"Bạn là chuyên gia thẩm định Sử học Việt Nam (Academic Reviewer AI).\n"
        f"Hãy tiến hành thẩm định và phản tư cực kỳ nghiêm ngặt câu trả lời lịch sử sau:\n\n"
        f"CÂU TRẢ LỜI NHÁP:\n{answer}\n\n"
        f"BỐI CẢNH LỊCH SỬ THỰC TẾ (DỮ LIỆU ĐÃ KIỂM CHỨNG):\n"
        f"1. Niên biểu lịch sử:\n{state.get('timeline_events', [])}\n"
        f"2. Phân đoạn văn bản nguồn:\n{[c.get('content', '')[:300] for c in state.get('retrieved_chunks', [])]}\n\n"
        f"TIÊU CHÍ THẨM ĐỊNH BẮT BUỘC:\n"
        f"1. Xung đột Niên biểu: Sự kiện lịch sử có bị nói sai mốc thời gian hoặc sai thứ tự nhân quả (trước/sau) so với Niên biểu thực tế không?\n"
        f"2. Hallucination: Có bất kỳ khẳng định, con số hoặc nhân vật nào xuất hiện trong câu trả lời nháp mà HOÀN TOÀN không thể tìm thấy hoặc suy luận từ văn bản nguồn không?\n"
        f"3. Trích dẫn (Citations): Trích dẫn nguồn dẫn đã chính xác và khách quan chưa?\n\n"
        f"Trả về kết quả dưới dạng JSON thuần túy:\n"
        f"{{\n"
        f"  \"approved\": true/false, # Chỉ approve khi hoàn toàn không có lỗi logic/hallucination\n"
        f"  \"feedback\": \"lý do chi tiết từ chối hoặc phê duyệt\"\n"
        f"}}"
    )

    llm = get_llm_client()
    approved = True
    feedback = "Approved."
    status = "success"

    try:
        resp = await llm.generate(prompt, system="You are a strict, academic history reviewer AI.", max_tokens=500)
        if resp.startswith("[Phản hồi từ bộ nhớ tạm"):
            status = "failed"
        parsed = parse_llm_json(resp)
        approved = parsed.get("approved", True)
        feedback = parsed.get("feedback", "No issues detected.")
    except Exception as exc:
        logger.error("agent_critic_validation_failed", error=str(exc))
        status = "failed"

    # Overrule approval if programmatic grounding checks fail
    if not has_grounding and approved:
        approved = False
        feedback = "Thẩm định tự động thất bại: Không tìm thấy trích dẫn hoặc tài liệu tham chiếu hợp lệ trong câu trả lời."

    # Trigger replanning loop if critique fails and limit has not been reached
    if not approved and replanning_count < 2:
        logger.warning("agentic_critic_rejected_answer", feedback=feedback)
        trace.append(
            {
                "agent": "Critic Agent (Reflection Loop)",
                "action": f"BẮC BỎ: {feedback}. Kích hoạt quy trình tự sửa lỗi và tái lập kế hoạch truy vấn...",
                "status": "failed",
            }
        )
        return {
            "replanning_required": True,
            "critic_feedback": feedback,
            "agent_trace": trace,
        }

    # Passed critique
    trace.append(
        {
            "agent": "Critic Agent",
            "action": f"THÔNG QUA: Kiểm chứng tri thức lịch sử thành công. Ý kiến: {feedback}" if status == "success" else "Lỗi kết nối LLM khi thực hiện thẩm định.",
            "status": status,
        }
    )

    return {
        "replanning_required": False,
        "critic_feedback": None,
        "agent_trace": trace,
    }


async def memory_consolidation_node(state: AgentState) -> dict[str, Any]:
    """Memory Consolidation agent: extracts discoveries, contradictions, updates long-term memory."""
    query = state["query"]
    answer = state.get("answer", "")
    trace = list(state.get("agent_trace", []))

    logger.info("agent_memory_consolidation_running", query=query[:50])

    prompt = (
        f"Đọc câu trả lời nghiên cứu lịch sử sau:\n{answer}\n\n"
        f"Hãy trích xuất những mối quan hệ thực thể lịch sử mới phát hiện, hoặc mâu thuẫn tri thức mới.\n"
        f"Trả về JSON dạng:\n"
        f"{{\n"
        f"  \"drafts\": [\n"
        f"    {{\n"
        f"      \"change_type\": \"add_node\" hoặc \"add_edge\" hoặc \"contradiction\",\n"
        f"      \"draft_data\": {{\n"
        f"         # nếu node: node_type, name, slug, description\n"
        f"         # nếu edge: source_slug, target_slug, edge_type, description, weight\n"
        f"         # nếu contradiction: entity_slug, field, old_value, new_value, description\n"
        f"      }}\n"
        f"    }}\n"
        f"  ]\n"
        f"}}"
    )

    llm = get_llm_client()
    drafts = []
    status = "success"
    try:
        resp = await llm.generate(prompt, system="You are a knowledge extraction agent.", max_tokens=1000)
        if resp.startswith("[Phản hồi từ bộ nhớ tạm"):
            status = "failed"
        parsed = parse_llm_json(resp)
        drafts = parsed.get("drafts", [])
    except Exception as exc:
        logger.error("agent_memory_consolidation_extraction_failed", error=str(exc))
        status = "failed"

    # Persist draft proposals into PostgreSQL knowledge_drafts table
    saved_count = 0
    if drafts and status == "success":
        try:
            async with get_db_context() as db:
                for d in drafts:
                    draft_obj = KnowledgeDraft(
                        change_type=d.get("change_type", "add_node"),
                        status="pending",
                        draft_data=d.get("draft_data", {}),
                        source_info={"query": query, "session_id": state.get("session_id")},
                    )
                    db.add(draft_obj)
                saved_count = len(drafts)
        except Exception as exc:
            logger.error("agent_memory_consolidation_saving_failed", error=str(exc))

    trace.append(
        {
            "agent": "Memory Consolidation Agent",
            "action": f"Phân tích hoàn tất. Trích xuất {saved_count} đề xuất tri thức lịch sử đưa vào hàng chờ kiểm duyệt (HITL)." if status == "success" else "Lỗi kết nối LLM khi phân tích đề xuất tri thức lịch sử.",
            "status": status,
        }
    )

    return {
        "draft_knowledge": drafts,
        "agent_trace": trace,
    }


# ------------------------------------------------------------------
# Conditional Routing Logic
# ------------------------------------------------------------------


def route_supervisor(state: AgentState) -> str:
    """Decides what the next node is based on plan step and execution_mode."""
    plan = state.get("plan", [])
    current_step = state.get("current_step", 0)
    mode = state.get("execution_mode", "agentic")

    if current_step < len(plan):
        return plan[current_step]

    # Plan exhausted — decide next phase by mode
    if mode == "agentic":
        return "world_model_node"   # full pipeline: world_model → reasoning → critic
    else:
        return "reasoning_node"     # fast & graph: skip world_model, go straight to reasoning


def route_after_reasoning(state: AgentState) -> str:
    """After reasoning: critic only in agentic mode, else END directly."""
    mode = state.get("execution_mode", "agentic")
    if mode == "agentic":
        return "critic_node"
    return "memory_consolidation_node"


def route_critic(state: AgentState) -> str:
    """Routes based on critic result. Replanning only in agentic mode."""
    if state.get("replanning_required"):
        return "supervisor_node"
    return "memory_consolidation_node"


# ------------------------------------------------------------------
# LangGraph Workflow Construction
# ------------------------------------------------------------------
# Three execution paths via execution_mode:
#
#  fast    → supervisor → retrieval → reasoning → memory_consolidation → END
#  graph   → supervisor → retrieval → graph → timeline → reasoning → memory → END
#  agentic → supervisor → retrieval → graph → timeline → world_model → reasoning → critic → memory → END
# ------------------------------------------------------------------

workflow = StateGraph(AgentState)

# Register Nodes
workflow.add_node("supervisor_node", supervisor_node)
workflow.add_node("retrieval_node", retrieval_node)
workflow.add_node("timeline_node", timeline_node)
workflow.add_node("graph_node", graph_node)
workflow.add_node("world_model_node", world_model_node)
workflow.add_node("reasoning_node", reasoning_node)
workflow.add_node("critic_node", critic_node)
workflow.add_node("memory_consolidation_node", memory_consolidation_node)

# Entry point
workflow.set_entry_point("supervisor_node")

# Supervisor: conditional routing by plan step + mode
workflow.add_conditional_edges(
    "supervisor_node",
    route_supervisor,
    {
        "retrieval_node": "retrieval_node",
        "timeline_node": "timeline_node",
        "graph_node": "graph_node",
        "world_model_node": "world_model_node",  # agentic only
        "reasoning_node": "reasoning_node",      # fast + graph shortcut
    },
)

# Search nodes loop back to supervisor
workflow.add_edge("retrieval_node", "supervisor_node")
workflow.add_edge("timeline_node", "supervisor_node")
workflow.add_edge("graph_node", "supervisor_node")

# Agentic: world_model feeds reasoning
workflow.add_edge("world_model_node", "reasoning_node")

# Reasoning: route to critic (agentic) OR memory_consolidation (fast/graph)
workflow.add_conditional_edges(
    "reasoning_node",
    route_after_reasoning,
    {
        "critic_node": "critic_node",
        "memory_consolidation_node": "memory_consolidation_node",
    },
)

# Critic: replanning (agentic) OR memory consolidation
workflow.add_conditional_edges(
    "critic_node",
    route_critic,
    {
        "supervisor_node": "supervisor_node",
        "memory_consolidation_node": "memory_consolidation_node",
    },
)

# Memory consolidation always ends
workflow.add_edge("memory_consolidation_node", END)

# Compile with checkpointing to prevent unbounded memory growth from accumulated state.
# Without a checkpointer, LangGraph accumulates checkpoints indefinitely across invocations.
checkpointer = MemorySaver()
agent_graph = workflow.compile(checkpointer=checkpointer)
