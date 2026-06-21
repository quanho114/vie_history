"""Out of Scope Workflow."""

from app.core.logging import get_logger

logger = get_logger("out_of_scope_workflow")


class OutOfScopeWorkflow:
    """
    Workflow for queries outside the domain scope.

    Returns the standard Vietnamese refusal format.
    """

    REFUSAL_MESSAGE = (
        "Chào bạn! Mình là HistoriAI, trợ lý chuyên sâu về Lịch sử Việt Nam. 🇻🇳\n\n"
        "Mặc dù rất muốn chia sẻ thêm với bạn về các chủ đề thú vị ngoài lề (như bóng đá, giải trí hay đời sống), "
        "nhưng để đảm bảo độ chính xác cao nhất, mình chỉ tập trung hỗ trợ các câu hỏi liên quan đến Lịch sử Việt Nam qua các thời kỳ, các trận đánh vang dội, niên biểu các triều đại hoặc phân tích nhân vật lịch sử.\n\n"
        "Nếu bạn có câu hỏi nào về Lịch sử Việt Nam, hãy chia sẻ cùng mình nhé! 😊"
    )

    async def execute(self, query: str) -> dict:
        """Execute out-of-scope workflow."""
        logger.info("out_of_scope_workflow_execute", query=query[:50])
        return {
            "answer": self.REFUSAL_MESSAGE,
            "chunks": [],
            "workflow": "out_of_scope",
        }
