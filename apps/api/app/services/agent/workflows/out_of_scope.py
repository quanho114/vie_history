"""Out of Scope Workflow."""

from app.core.logging import get_logger

logger = get_logger("out_of_scope_workflow")


class OutOfScopeWorkflow:
    """
    Workflow for queries outside the domain scope.

    Returns the standard Vietnamese refusal format.
    """

    REFUSAL_MESSAGE = (
        "HistoriAI chuyên hỗ trợ nghiên cứu và tra cứu lịch sử Việt Nam.\n\n"
        "Câu hỏi của bạn nằm ngoài phạm vi chuyên môn của hệ thống, nên tôi không thể cung cấp câu trả lời đáng tin cậy.\n\n"
        "Bạn có thể hỏi về:\n"
        "• Các triều đại Việt Nam\n"
        "• Nhân vật lịch sử\n"
        "• Các cuộc kháng chiến\n"
        "• Sự kiện lịch sử Việt Nam\n"
        "• Chính sách và cải cách qua các thời kỳ"
    )

    async def execute(self, query: str) -> dict:
        """Execute out-of-scope workflow."""
        logger.info("out_of_scope_workflow_execute", query=query[:50])
        return {
            "answer": self.REFUSAL_MESSAGE,
            "chunks": [],
            "workflow": "out_of_scope",
        }
