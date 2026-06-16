"""FastAPI dependency injection container.

Implements the "Explicit > Implicit" principle: every service dependency
is declared explicitly at the route layer, making the dependency graph
inspectable and testable.

Usage:
    from app.containers import get_db, get_orchestrator, get_query_service

    @router.post("/query")
    async def query_endpoint(
        db: AsyncSession = Depends(get_db),
        orchestrator: AgentOrchestrator = Depends(get_orchestrator),
    ):
        ...
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, AsyncGenerator

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.agent.classifier import IntentClassifier
    from app.services.agent.planner import TaskPlanner
    from app.services.agent.verifier import Verifier
    from app.services.agent.response_builder import ResponseBuilder
    from app.services.agent.safety_integration import SafetyIntegration
    from app.services.retrieval.query_service import QueryService
    from app.services.retrieval.embedder import Embedder
    from app.services.retrieval.vector_search import VectorSearch
    from app.services.retrieval.fusion import FusionSearch
    from app.services.llm.client import BaseLLMClient
    from app.services.brain.brain_router import BrainRouter
    from app.services.brain.context_composer import ContextComposer
    from app.agents.orchestrator import AgentOrchestrator


# ─── Container ─────────────────────────────────────────────────────────────────


@dataclass
class AppContainer:
    """Explicit dependency container for FastAPI injection.

    All services are lazily initialized and cached per container instance.
    For testing, create a container with overrides::

        container = AppContainer(
            embedder=MockEmbedder(),
            llm_client=MockLLMClient(),
        )
    """

    _embedder: Embedder | None = field(default=None, repr=False)
    _vector_search: VectorSearch | None = field(default=None, repr=False)
    _fusion: FusionSearch | None = field(default=None, repr=False)
    _query_service: QueryService | None = field(default=None, repr=False)
    _classifier: IntentClassifier | None = field(default=None, repr=False)
    _planner: TaskPlanner | None = field(default=None, repr=False)
    _verifier: Verifier | None = field(default=None, repr=False)
    _response_builder: ResponseBuilder | None = field(default=None, repr=False)
    _brain_router: BrainRouter | None = field(default=None, repr=False)
    _context_composer: ContextComposer | None = field(default=None, repr=False)
    _safety_integration: SafetyIntegration | None = field(default=None, repr=False)
    _orchestrator: AgentOrchestrator | None = field(default=None, repr=False)
    _init_lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    # ─── Embedder ───────────────────────────────────────────────────────────

    def get_embedder(self) -> Embedder:
        if self._embedder is None:
            from app.services.retrieval.embedder import Embedder
            self._embedder = Embedder()
        return self._embedder

    # ─── Vector Search ─────────────────────────────────────────────────────

    def get_vector_search(self) -> VectorSearch:
        if self._vector_search is None:
            from app.services.retrieval.vector_search import VectorSearch
            self._vector_search = VectorSearch()
        return self._vector_search

    # ─── Fusion ────────────────────────────────────────────────────────────

    def get_fusion(self) -> FusionSearch:
        if self._fusion is None:
            from app.services.retrieval.fusion import FusionSearch
            self._fusion = FusionSearch(rrf_k=60)
        return self._fusion

    # ─── Query Service ─────────────────────────────────────────────────────

    def get_query_service(self) -> QueryService:
        if self._query_service is None:
            self._query_service = QueryService(
                embedder=self.get_embedder(),
                vector_search=self.get_vector_search(),
                fusion=self.get_fusion(),
                candidate_size=20,
                final_top_k=5,
            )
        return self._query_service

    # ─── Classifier ────────────────────────────────────────────────────────

    def get_classifier(self) -> IntentClassifier:
        if self._classifier is None:
            from app.services.agent.classifier import IntentClassifier
            self._classifier = IntentClassifier()
        return self._classifier

    # ─── Planner ───────────────────────────────────────────────────────────

    def get_planner(self) -> TaskPlanner:
        if self._planner is None:
            from app.services.agent.planner import TaskPlanner
            self._planner = TaskPlanner()
        return self._planner

    # ─── Verifier ──────────────────────────────────────────────────────────

    def get_verifier(self) -> Verifier:
        if self._verifier is None:
            from app.services.agent.verifier import Verifier
            self._verifier = Verifier(min_evidence=1)
        return self._verifier

    # ─── Response Builder ──────────────────────────────────────────────────

    def get_response_builder(self) -> ResponseBuilder:
        if self._response_builder is None:
            from app.services.agent.response_builder import ResponseBuilder
            self._response_builder = ResponseBuilder()
        return self._response_builder

    # ─── Brain Router ─────────────────────────────────────────────────────

    def get_brain_router(self) -> BrainRouter:
        if self._brain_router is None:
            from app.services.brain.brain_router import BrainRouter
            self._brain_router = BrainRouter()
        return self._brain_router

    # ─── Context Composer ──────────────────────────────────────────────────

    def get_context_composer(self) -> ContextComposer:
        if self._context_composer is None:
            from app.services.brain.context_composer import ContextComposer
            self._context_composer = ContextComposer()
        return self._context_composer

    # ─── Safety Integration ────────────────────────────────────────────────

    def get_safety_integration(self) -> SafetyIntegration:
        if self._safety_integration is None:
            from app.services.agent.safety_integration import get_safety_integration
            self._safety_integration = get_safety_integration()
        return self._safety_integration

    # ─── Agent Orchestrator ────────────────────────────────────────────────

    def get_orchestrator(self) -> AgentOrchestrator:
        if self._orchestrator is None:
            from app.agents.orchestrator import AgentOrchestrator
            self._orchestrator = AgentOrchestrator(
                classifier=self.get_classifier(),
                planner=self.get_planner(),
                retriever=self.get_query_service(),
                verifier=self.get_verifier(),
                response_builder=self.get_response_builder(),
            )
        return self._orchestrator


# ─── Global Container (singleton per process) ────────────────────────────────


_container: AppContainer | None = None


def get_container() -> AppContainer:
    """Get or create the global application container."""
    global _container
    if _container is None:
        _container = AppContainer()
    return _container


def reset_container() -> None:
    """Reset container — for testing only."""
    global _container
    _container = None


# ─── FastAPI Dependency Injection ────────────────────────────────────────────


def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Database session dependency."""
    from app.core.database import async_session
    return async_session()


def get_llm() -> BaseLLMClient:
    """LLM client dependency."""
    from app.services.llm.client import get_llm_client
    return get_llm_client()


def get_orchestrator() -> AgentOrchestrator:
    """Agent orchestrator dependency (singleton per container)."""
    return get_container().get_orchestrator()


def get_query_service() -> QueryService:
    """Query service dependency (singleton per container)."""
    return get_container().get_query_service()


def get_safety() -> SafetyIntegration:
    """Safety integration dependency."""
    return get_container().get_safety_integration()


def get_classifier() -> IntentClassifier:
    """Intent classifier dependency."""
    return get_container().get_classifier()


def get_planner() -> TaskPlanner:
    """Task planner dependency."""
    return get_container().get_planner()


def get_brain_router() -> BrainRouter:
    """Brain router dependency."""
    return get_container().get_brain_router()


def get_context_composer() -> ContextComposer:
    """Context composer dependency."""
    return get_container().get_context_composer()
