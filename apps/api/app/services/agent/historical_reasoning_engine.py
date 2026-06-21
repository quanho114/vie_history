import json
import re
from typing import Any
from app.services.llm.client import get_llm_client
from app.core.logging import get_logger

logger = get_logger("historical_reasoning_engine")

class HistoricalReasoningEngine:
    """
    Causal World Reasoning Engine for Vietnamese history.
    Analyzes causes, triggers, turning points, immediate consequences, and long-term impacts
    based on retrieved timeline events and source document chunks.
    """

    def __init__(self):
        try:
            self.llm = get_llm_client()
        except Exception as exc:
            logger.warning("failed_to_initialize_llm_client_for_reasoning_engine", error=str(exc))
            self.llm = None

    async def analyze_causality(self, query: str, chunks: list[dict[str, Any]], timeline_events: list[dict[str, Any]] = None) -> dict[str, Any]:
        """
        Runs causal reasoning analyzing triggers, turning points, consequences, and long term impacts.
        """
        if not self.llm:
            return {
                "causes": ["Không thể phân tích bối cảnh tự động (Thiếu LLM)."],
                "triggers": ["Không thể xác định ngòi nổ kích hoạt (Thiếu LLM)."],
                "turning_points": ["Không tìm thấy bước ngoặt (Thiếu LLM)."],
                "consequences": ["Không thể trích xuất kết quả (Thiếu LLM)."],
                "long_term_impacts": ["Lỗi phân tích ý nghĩa lịch sử (Thiếu LLM)."]
            }

        timeline_events = timeline_events or []
        
        # Prepare content strings
        chunks_str = "\n\n".join([f"- Document Chunk: {c.get('content', '')}" for c in chunks if c.get('content')])
        events_str = "\n".join([f"- Event in {e.get('year', '?')}: {e.get('title', '')} - {e.get('description', '')}" for e in timeline_events])

        prompt = (
            f"Bạn là Trí tuệ Phân tích Nhân quả Lịch sử Việt Nam (Historical Causal Reasoning Engine).\n"
            f"Nhiệm vụ của bạn là phân tích mối quan hệ nguyên nhân - kết quả cho câu hỏi lịch sử sau:\n"
            f"Câu hỏi: \"{query}\"\n\n"
            f"Dựa trên các tư liệu lịch sử dưới đây:\n"
            f"1. Trích dẫn tài liệu:\n{chunks_str}\n\n"
            f"2. Sự kiện dòng thời gian:\n{events_str}\n\n"
            f"Hãy phân tích và trả về cấu trúc JSON thuần túy (không chứa markdown, không nằm trong ```json):\n"
            f"{{\n"
            f"  \"causes\": [\"Mảng nguyên nhân sâu xa hoặc bối cảnh dẫn tới sự kiện\"],\n"
            f"  \"triggers\": [\"Mảng nguyên nhân trực tiếp hoặc sự kiện kích ngòi\"],\n"
            f"  \"turning_points\": [\"Mảng các bước ngoặt quan trọng trong tiến trình diễn biến\"],\n"
            f"  \"consequences\": [\"Mảng kết quả hoặc hậu quả trực tiếp ngắn hạn\"],\n"
            f"  \"long_term_impacts\": [\"Mảng ảnh hưởng hoặc ý nghĩa lịch sử lâu dài\"]\n"
            f"}}\n"
        )

        try:
            resp = await self.llm.generate(
                prompt,
                system="Bạn là chuyên gia sử học Việt Nam chuyên phân tích nhân quả lịch sử.",
                max_tokens=600
            )
            
            # Safe JSON parsing
            clean_resp = resp.strip()
            if clean_resp.startswith("```"):
                # strip code block formatting if present
                clean_resp = re.sub(r"^```(?:json)?\n", "", clean_resp)
                clean_resp = re.sub(r"\n```$", "", clean_resp)
            
            # Find JSON boundaries
            start = clean_resp.find("{")
            end = clean_resp.rfind("}")
            if start != -1 and end != -1:
                clean_resp = clean_resp[start:end+1]
                
            parsed = json.loads(clean_resp)
            logger.info("causal_analysis_success", query=query[:30])
            return {
                "causes": parsed.get("causes", []),
                "triggers": parsed.get("triggers", []),
                "turning_points": parsed.get("turning_points", []),
                "consequences": parsed.get("consequences", []),
                "long_term_impacts": parsed.get("long_term_impacts", [])
            }
        except Exception as exc:
            logger.error("causal_analysis_failed_using_fallback", error=str(exc))
            # Graceful fallback structure
            return {
                "causes": ["Không thể phân tích bối cảnh tự động."],
                "triggers": ["Không thể xác định ngòi nổ kích hoạt."],
                "turning_points": ["Không tìm thấy bước ngoặt."],
                "consequences": ["Không thể trích xuất kết quả."],
                "long_term_impacts": ["Lỗi phân tích ý nghĩa lịch sử."]
            }
