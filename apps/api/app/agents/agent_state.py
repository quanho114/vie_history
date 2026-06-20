from typing import TypedDict, Annotated, Sequence, Any
import operator

class AgentState(TypedDict):
    query: str
    intent: str
    plan: list[dict[str, Any]]
    retrieved_docs: Annotated[list[dict], operator.add]
    reasoning_trace: Annotated[list[str], operator.add]
    confidence: float
    errors: list[str]
    retry_count: int
    final_answer: str
