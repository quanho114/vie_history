"""Graph Workflow — multi-hop knowledge graph reasoning."""

from app.core.logging import get_logger
from app.services.agent.workflows.base import BaseWorkflow

logger = get_logger("graph_workflow")


class GraphWorkflow(BaseWorkflow):
    """
    Workflow for graph-based multi-hop reasoning queries.

    Steps:
    1. Extract entity mentions from query
    2. Resolve entities to graph nodes
    3. Traverse graph for multi-hop connections
    4. Extract paths and synthesize answer

    Note: This workflow delegates to the GraphReasoner and Neo4jService
    for actual graph traversal. This class provides the orchestration
    layer and prompt construction.
    """

    async def execute(self, state) -> dict:
        """Execute graph workflow."""
        raise NotImplementedError(
            "GraphWorkflow is not yet implemented. "
            "Graph queries currently fall through to the LangGraph agent_graph."
        )
