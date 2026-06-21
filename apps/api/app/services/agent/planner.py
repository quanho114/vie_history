"""Task and Historical Planner services."""

from dataclasses import dataclass, field
from typing import Dict, Any
from app.core.logging import get_logger

logger = get_logger("task_planner")


@dataclass
class RetrievalPlan:
    """Plan for retrieval operations."""

    search_query: str
    filters: dict | None = None
    top_k: int = 5


@dataclass
class TaskPlan:
    """Full task execution plan."""

    workflow: str
    retrieval_plans: list[RetrievalPlan]
    metadata_filters: dict | None = None


# ------------------------------------------------------------------
# Tool Registry definition
# ------------------------------------------------------------------
AVAILABLE_TOOLS = {
    "retrieval": "retrieval_node",
    "graph": "graph_node",
    "timeline": "timeline_node",
    "world_model": "world_model_node"
}


class HistoricalPlanner:
    """
    Research-grade planner generating dynamic JSON plans and validating them
    against the AVAILABLE_TOOLS registry to prevent hallucination.
    """

    def __init__(self):
        try:
            from app.services.llm.client import get_llm_client
            self.llm = get_llm_client()
        except Exception as e:
            logger.warning("failed_to_initialize_llm_client_for_planner", error=str(e))
            self.llm = None

    async def create_plan(self, query: str) -> Dict[str, Any]:
        """
        Formulate a dynamic tool execution plan for a historical query.
        """
        from app.services.agent.query_analyzer import QueryAnalyzer
        analyzer = QueryAnalyzer()
        if analyzer.is_simple_query(query):
            logger.info("routing_simple_query_bypassing_agents", query=query)
            return {"tasks": [{"tool": "retrieval", "reason": "Factual/simple query bypassing graph/world model."}]}

        if not self.llm:
            return {"tasks": [{"tool": "retrieval", "reason": "Fallback retrieval step due to missing LLM."}]}

        prompt = (
            f"Bạn là Trí tuệ Điều phối Lịch sử Việt Nam (Autonomous History Planner AI).\n"
            f"Nhiệm vụ của bạn là phân tích câu hỏi nghiên cứu lịch sử của người dùng:\n"
            f"\"{query}\"\n\n"
            f"Hãy sinh ra một kế hoạch thực thi dưới dạng JSON thuần túy có cấu trúc:\n"
            f"{{\n"
            f"  \"tasks\": [\n"
            f"    {{\n"
            f"      \"tool\": \"retrieval\" | \"graph\" | \"timeline\" | \"world_model\",\n"
            f"      \"reason\": \"Lý do chi tiết vì sao cần sử dụng công cụ này\"\n"
            f"    }}\n"
            f"  ]\n"
            f"}}\n\n"
            f"Quy tắc lập kế hoạch:\n"
            f"- Luôn cần 'retrieval' cho bằng chứng tài liệu.\n"
            f"- Cần 'graph' nếu có phân tích mối quan hệ nhân vật, triều đại, sự kiện liên kết.\n"
            f"- Cần 'timeline' nếu hỏi về trình tự thời gian, so sánh thời kỳ hoặc mốc năm cụ thể."
        )
        try:
            from app.services.llm.json_parser import parse_llm_json
            resp = await self.llm.generate(prompt, system="You are an academic planner.", max_tokens=500)
            parsed = parse_llm_json(resp)
            return self.validate_plan(parsed)
        except Exception as exc:
            logger.error("planner_failed_default_to_fallback", error=str(exc))
            return {"tasks": [{"tool": "retrieval", "reason": "Error fallback."}]}

    def validate_plan(self, raw_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filters out any tools that are not in the AVAILABLE_TOOLS registry.
        """
        validated_tasks = []
        for task in raw_plan.get("tasks", []):
            tool_name = task.get("tool")
            if tool_name in AVAILABLE_TOOLS:
                validated_tasks.append(task)
            else:
                logger.warning("filtered_hallucinated_tool", tool=tool_name)
        if not validated_tasks:
            validated_tasks = [{"tool": "retrieval", "reason": "Registry fallback default task."}]
        return {"tasks": validated_tasks}


class TaskPlanner:
    """
    Plans how to execute a query based on classified intent (legacy).
    """

    def plan(self, intent: str, query: str, raw_query: str) -> TaskPlan:
        """
        Generate execution plan for the given intent and query.
        """
        logger.info("planning_task", intent=intent, query=query[:50])

        if intent == "factual":
            return self._plan_factual(raw_query)
        elif intent == "timeline":
            return self._plan_timeline(raw_query)
        elif intent == "compare":
            return self._plan_compare(raw_query)
        elif intent == "summary":
            return self._plan_summary(raw_query)
        elif intent == "source_audit":
            return self._plan_source_audit(raw_query)
        else:
            return self._plan_out_of_scope(raw_query)

    def _plan_factual(self, query: str) -> TaskPlan:
        return TaskPlan(
            workflow="factual_workflow",
            retrieval_plans=[
                RetrievalPlan(
                    search_query=query,
                    top_k=5,
                ),
            ],
            metadata_filters=None,
        )

    def _plan_timeline(self, query: str) -> TaskPlan:
        years = self._extract_years(query)

        filters = {}
        if years:
            filters["year_range"] = years

        return TaskPlan(
            workflow="timeline_workflow",
            retrieval_plans=[
                RetrievalPlan(
                    search_query=query,
                    filters=filters,
                    top_k=20,
                ),
            ],
            metadata_filters=filters if filters else None,
        )

    def _plan_compare(self, query: str) -> TaskPlan:
        subjects = self._extract_compare_subjects(query)

        plans = [
            RetrievalPlan(search_query=subj, top_k=5)
            for subj in subjects
        ]

        return TaskPlan(
            workflow="compare_workflow",
            retrieval_plans=plans,
            metadata_filters=None,
        )

    def _plan_summary(self, query: str) -> TaskPlan:
        return TaskPlan(
            workflow="summary_workflow",
            retrieval_plans=[
                RetrievalPlan(
                    search_query=query,
                    top_k=10,
                ),
            ],
            metadata_filters=None,
        )

    def _plan_source_audit(self, query: str) -> TaskPlan:
        return TaskPlan(
            workflow="source_audit_workflow",
            retrieval_plans=[
                RetrievalPlan(
                    search_query=query,
                    top_k=15,
                ),
            ],
            metadata_filters=None,
        )

    def _plan_out_of_scope(self, query: str) -> TaskPlan:
        return TaskPlan(
            workflow="out_of_scope_workflow",
            retrieval_plans=[],
            metadata_filters=None,
        )

    def _extract_years(self, query: str) -> tuple[int, int] | None:
        from app.services.agent.temporal_extractor import HistoricalTemporalExtractor
        result = HistoricalTemporalExtractor().extract(query)
        start = result.get("start_year")
        end = result.get("end_year")
        if start is not None and end is not None:
            return (start, end)
        if start is not None:
            return (start, start)
        return None

    def _extract_compare_subjects(self, query: str) -> list[str]:
        separators = ["và", "vs", "với", "so với", "between", "and"]
        for sep in separators:
            if sep in query.lower():
                parts = query.lower().split(sep)
                return [p.strip() for p in parts if p.strip()]
        return [query]
