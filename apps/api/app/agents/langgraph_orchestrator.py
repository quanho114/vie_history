from typing import Dict, Any
from langgraph.graph import StateGraph, END
from app.agents.agent_state import AgentState

class LangGraphOrchestrator:
    def __init__(self):
        workflow = StateGraph(AgentState)
        
        # Add Nodes
        workflow.add_node("classify_intent", self._classify_intent)
        workflow.add_node("plan_steps", self._plan_steps)
        workflow.add_node("retrieve_knowledge", self._retrieve_knowledge)
        workflow.add_node("verify_evidence", self._verify_evidence)
        workflow.add_node("synthesize_answer", self._synthesize_answer)
        workflow.add_node("critic", self._critic_evaluation)
        workflow.add_node("re_plan", self._re_plan)

        # Set Entrypoint
        workflow.set_entry_point("classify_intent")

        # Define Transitions
        workflow.add_edge("classify_intent", "plan_steps")
        workflow.add_edge("plan_steps", "retrieve_knowledge")
        workflow.add_edge("retrieve_knowledge", "verify_evidence")
        workflow.add_edge("verify_evidence", "synthesize_answer")
        workflow.add_edge("synthesize_answer", "critic")
        
        workflow.add_conditional_edges(
            "critic",
            self._decide_routing,
            {
                "sufficient": END,
                "insufficient": "re_plan"
            }
        )
        
        workflow.add_edge("re_plan", "retrieve_knowledge")
        
        self.app = workflow.compile()

    def _classify_intent(self, state: AgentState) -> Dict[str, Any]:
        return {"intent": "factual", "reasoning_trace": ["Classified query intent."]}

    def _plan_steps(self, state: AgentState) -> Dict[str, Any]:
        return {"plan": [{"type": "search", "query": state["query"]}], "reasoning_trace": ["Created plan."]}

    async def _retrieve_knowledge(self, state: AgentState) -> Dict[str, Any]:
        # Perform Vector/BM25 retrieval logic
        return {"retrieved_docs": [{"content": "Tài liệu mẫu về chiến dịch Bạch Đằng."}], "reasoning_trace": ["Fetched source documents."]}

    def _verify_evidence(self, state: AgentState) -> Dict[str, Any]:
        # Temporary logic for state progression
        confidence = 0.8 if state["retry_count"] > 0 else 0.4
        return {"confidence": confidence, "reasoning_trace": [f"Calculated confidence: {confidence}"]}

    def _decide_routing(self, state: AgentState) -> str:
        if state["confidence"] >= 0.7 or state["retry_count"] >= 2:
            return "sufficient"
        return "insufficient"

    def _re_plan(self, state: AgentState) -> Dict[str, Any]:
        return {
            "retry_count": state.get("retry_count", 0) + 1,
            "plan": [{"type": "expanded_search", "query": state["query"]}],
            "reasoning_trace": ["Triggered replan."]
        }

    async def _critic_evaluation(self, state: AgentState) -> Dict[str, Any]:
        draft = state["final_answer"]
        query = state["query"]
        
        # Simulating critic scoring (to be replaced by actual LLM check in service layer)
        if "tại sao" in query.lower() and "chính trị" not in draft.lower() and state["retry_count"] == 0:
            return {
                "confidence": 0.5,
                "reasoning_trace": ["Critic found missing perspective: political factors."]
            }
        return {"confidence": 0.9, "reasoning_trace": ["Critic passed the response."]}

    async def _synthesize_answer(self, state: AgentState) -> Dict[str, Any]:
        return {"final_answer": "Vua Quang Trung đại phá quân Thanh.", "reasoning_trace": ["Synthesized answer."]}

    async def run(self, query: str) -> Dict[str, Any]:
        initial_state = {
            "query": query,
            "intent": "",
            "plan": [],
            "retrieved_docs": [],
            "reasoning_trace": [],
            "confidence": 0.0,
            "errors": [],
            "retry_count": 0,
            "final_answer": ""
        }
        return await self.app.ainvoke(initial_state)
