"""Out of Scope Workflow."""

from app.core.logging import get_logger

logger = get_logger("out_of_scope_workflow")


class OutOfScopeWorkflow:
    """
    Workflow for queries outside the domain scope.

    Returns clear scope explanation without deep processing.
    """

    SCOPE_MESSAGE_EN = (
        "This query is outside the scope of this AI research agent. "
        "This system focuses specifically on Vietnamese history from 1945 to 1975, "
        "including:\n\n"
        "- The August Revolution and establishment of the Democratic Republic of Vietnam\n"
        "- The First Indochina War (1946-1954)\n"
        "- The Geneva Accords (1954)\n"
        "- The Vietnam War / Second Indochina War (1955-1975)\n"
        "- Key events, figures, and organizations in this period\n\n"
        "Please rephrase your question to focus on Vietnamese history during 1945-1975, "
        "or contact the system administrator if you believe this is an error."
    )

    SCOPE_MESSAGE_VI = (
        "Câu hỏi này nằm ngoài phạm vi nghiên cứu của trợ lý AI.\n"
        "Hệ thống tập trung chuyên sâu vào Lịch sử Việt Nam giai đoạn từ năm 1945 đến năm 1975, "
        "bao gồm:\n\n"
        "- Cách mạng Tháng Tám và sự thành lập nước Việt Nam Dân chủ Cộng hòa\n"
        "- Chiến tranh Đông Dương / Kháng chiến chống Pháp (1946-1954)\n"
        "- Hiệp định Genève (1954)\n"
        "- Kháng chiến chống Mỹ / Chiến tranh Việt Nam (1955-1975)\n"
        "- Các sự kiện, nhân vật và tổ chức quan trọng trong thời kỳ này\n\n"
        "Vui lòng điều chỉnh lại câu hỏi tập trung vào lịch sử Việt Nam trong giai đoạn 1945-1975."
    )

    async def execute(self, query: str) -> dict:
        """Execute out-of-scope workflow."""
        logger.info("out_of_scope_workflow_execute", query=query[:50])

        # Attempt to dynamically use LLM to respond politely in Vietnamese
        try:
            from app.services.llm.client import get_llm_client
            client = get_llm_client()
            prompt = (
                f"Bạn là HistoriAI, trợ lý nghiên cứu Lịch sử Việt Nam (1945-1975) cực kỳ thân thiện, thông minh và dí nhỏm.\n"
                f"Người dùng vừa trò chuyện hoặc hỏi bạn một câu nằm ngoài phạm vi lịch sử Việt Nam 1945-1975: '{query}'.\n\n"
                f"HÃY THỰC HIỆN CÁC BƯỚC SAU:\n"
                f"1. Trả lời cực kỳ ngắn gọn, tự nhiên và vui vẻ trực tiếp câu hỏi/lời chào của họ (ví dụ: nếu họ hỏi về Lionel Messi, bóng đá, hoặc chào hỏi xã giao, hãy đối đáp ngắn gọn 1-2 câu để thể hiện sự thông minh và gần gũi).\n"
                f"2. Sau đó, khéo léo dẫn dắt (bridge) người dùng trở lại chuyên môn chính của bạn: Nghiên cứu Lịch sử Việt Nam giai đoạn 1945-1975 (như Cách mạng Tháng Tám, Kháng chiến chống Pháp/Mỹ, Điện Biên Phủ, Hiệp định Genève, v.v.) bằng một gợi ý thú vị."
            )
            llm_answer = await client.generate(prompt, max_tokens=256)
            if llm_answer and len(llm_answer.strip()) > 10:
                return {
                    "answer": llm_answer.strip(),
                    "chunks": [],
                    "workflow": "out_of_scope",
                }
        except Exception as exc:
            logger.warning("out_of_scope_llm_failed", error=str(exc))

        # Detect language to choose appropriate static message
        is_english = any(word in query.lower() for word in ["hello", "hi", "who are you", "what can you"])
        fallback_message = self.SCOPE_MESSAGE_EN if is_english else self.SCOPE_MESSAGE_VI

        return {
            "answer": fallback_message,
            "chunks": [],
            "workflow": "out_of_scope",
        }
