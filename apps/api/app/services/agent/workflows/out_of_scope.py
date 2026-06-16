"""Out of Scope Workflow."""

from app.core.logging import get_logger

logger = get_logger("out_of_scope_workflow")


class OutOfScopeWorkflow:
    """
    Workflow for queries outside the domain scope.

    Returns the standard Vietnamese refusal format.
    """

    REFUSAL_MESSAGE = (
        "Mình có thể hỗ trợ bạn tra cứu và phân tích lịch sử Việt Nam qua các thời kỳ. Ví dụ:\n"
        "• Tóm tắt các sự kiện lịch sử\n"
        "• Giải thích nguyên nhân và kết quả của các cuộc kháng chiến\n"
        "• Lập dòng thời gian sự kiện, niên biểu các triều đại\n"
        "• So sánh các nhân vật hoặc giai đoạn lịch sử\n"
        "• Trả lời câu hỏi dựa trên kho tài liệu lịch sử của hệ thống\n\n"
        "Ngoài lĩnh vực lịch sử Việt Nam, mình có thể không đưa ra được câu trả lời đáng tin cậy. Bạn muốn hỏi mình câu hỏi nào về lịch sử Việt Nam không?"
    )

    async def execute(self, query: str) -> dict:
        """Execute out-of-scope workflow."""
        logger.info("out_of_scope_workflow_execute", query=query[:50])
        return {
            "answer": self.REFUSAL_MESSAGE,
            "chunks": [],
            "workflow": "out_of_scope",
        }
