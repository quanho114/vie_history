import json
from typing import Dict, Any
from app.services.llm.client import get_llm_client
from app.services.llm.json_parser import parse_llm_json
from app.core.logging import get_logger

logger = get_logger("query_analyzer")

class QueryAnalyzer:
    """
    Analyzes historical query strings to extract structured metadata.
    
    Attributes:
        intent: The category of historical query (factual, timeline, comparison, cause_effect, multi_hop).
        entities: List of proper noun Vietnamese historical entities.
        time_range: A list [start_year, end_year] indicating temporal boundary constraint.
    """
    def __init__(self):
        try:
            self.llm = get_llm_client()
        except Exception as e:
            logger.warning("failed_to_initialize_llm_client", error=str(e))
            self.llm = None

    async def analyze(self, query: str) -> Dict[str, Any]:
        """
        Parses query using LLM and extracts semantic tokens and bounds.
        """
        if not self.llm:
            return self._fallback_analyze(query)

        prompt = (
            f"Bạn là chuyên gia phân tích ngữ nghĩa lịch sử Việt Nam (1945-1975).\n"
            f"Hãy phân tích câu hỏi nghiên cứu sau: \"{query}\"\n\n"
            f"Hãy trích xuất:\n"
            f"1. intent: Phân loại câu hỏi vào một trong các kiểu: factual, timeline, comparison, cause_effect, multi_hop.\n"
            f"2. entities: Mảng chứa các thực thể lịch sử chính (tên người, địa danh, tên chiến dịch, tổ chức, hiệp định).\n"
            f"3. time_range: Khoảng thời gian cụ thể được đề cập [năm_bắt_đầu, năm_kết_thúc]. Nếu không đề cập cụ thể, hãy ước lượng dựa trên thực thể, ví dụ Điện Biên Phủ thì ước lượng [1953, 1954].\n\n"
            f"Trả về kết quả dưới dạng JSON thuần túy có cấu trúc:\n"
            f"{{\n"
            f"  \"intent\": \"factual\" | \"timeline\" | \"comparison\" | \"cause_effect\" | \"multi_hop\",\n"
            f"  \"entities\": [\"thực thể 1\", \"thực thể 2\"],\n"
            f"  \"time_range\": [năm_bắt_đầu, năm_kết_thúc]\n"
            f"}}"
        )
        try:
            resp = await self.llm.generate(prompt, max_tokens=300)
            parsed = parse_llm_json(resp)
            return {
                "intent": parsed.get("intent", "factual"),
                "entities": parsed.get("entities", []),
                "time_range": parsed.get("time_range", [None, None])
            }
        except Exception as exc:
            logger.error("query_analyzer_failed", error=str(exc))
            return self._fallback_analyze(query)

    def _fallback_analyze(self, query: str) -> Dict[str, Any]:
        # Simple rule-based fallback for robustness
        query_lower = query.lower()
        intent = "factual"
        if any(kw in query_lower for kw in ["so sánh", "khác nhau", "giống nhau"]):
            intent = "comparison"
        elif any(kw in query_lower for kw in ["tại sao", "vì sao", "nguyên nhân", "hệ quả"]):
            intent = "cause_effect"
        elif any(kw in query_lower for kw in ["diễn biến", "trình tự", "timeline"]):
            intent = "timeline"
        elif any(kw in query_lower for kw in ["liên kết", "mối quan hệ", "chuỗi"]):
            intent = "multi_hop"

        # Regex extract years
        import re
        years = [int(y) for y in re.findall(r"\b\d{4}\b", query)]
        time_range = [min(years), max(years)] if years else [None, None]

        return {
            "intent": intent,
            "entities": [],
            "time_range": time_range
        }
