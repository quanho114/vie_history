"""Task Planner service."""

from dataclasses import dataclass

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


class TaskPlanner:
    """
    Plans how to execute a query based on classified intent.
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
        """Plan for factual lookup."""
        # Extract potential entities and dates for filtering
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
        """Plan for timeline queries."""
        # Extract year range if present
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
        """Plan for comparison queries."""
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
        """Plan for summary queries."""
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
        """Plan for source audit."""
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
        """Plan for out of scope queries."""
        return TaskPlan(
            workflow="out_of_scope_workflow",
            retrieval_plans=[],
            metadata_filters=None,
        )

    def _extract_years(self, query: str) -> tuple[int, int] | None:
        """Extract year range from query."""
        import re
        year_pattern = r"\b(19[4-9][0-9]|2000)\b"
        years = re.findall(year_pattern, query)
        if len(years) >= 2:
            return (int(years[0]), int(years[1]))
        elif len(years) == 1:
            return (int(years[0]), int(years[0]))
        return None

    def _extract_compare_subjects(self, query: str) -> list[str]:
        """Extract subjects being compared."""
        # Simple split by common comparison keywords
        separators = ["và", "vs", "với", "so với", "between", "and"]
        for sep in separators:
            if sep in query.lower():
                parts = query.lower().split(sep)
                return [p.strip() for p in parts if p.strip()]
        return [query]
