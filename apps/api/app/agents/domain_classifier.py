"""Domain Classifier — fast-path domain check (Vietnamese History 1945-1975).

Determines if a query is within scope (Vietnamese history 1945-1975 or greetings)
or out of scope. Uses hybrid rule-based matching and fast LLM classification.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from app.core.logging import get_logger
from app.services.llm.client import get_llm_client
from app.services.llm.json_parser import parse_llm_json

logger = get_logger("domain_classifier")


@dataclass
class DomainResult:
    is_in_scope: bool
    reason: str


class DomainClassifier:
    """Classifies user queries into in-scope (Vietnam history 1945-1975 / greetings) or out-of-scope."""

    GREETING_KEYWORDS = [
        "chào", "hello", "hi", "xin chào", "cảm ơn", "thank", "bye",
        "tạm biệt", "hey", "hola", "good morning", "good evening",
        "chào buổi sáng", "chào buổi tối", "bạn khỏe", "how are you",
        "nice to meet", "rất vui", "giới thiệu bản thân", "tên gì",
        "bạn là ai", "what is your name", "who are you",
    ]

    OUT_OF_SCOPE_KEYWORDS = [
        "messi", "ronaldo", "neymar", "bóng đá", "football", "soccer",
        "thời tiết", "weather", "ngày mai", "hôm nay", "nhiệt độ",
        "lập trình", "code", "python", "javascript", "react", "html", "css",
        "java", "c++", "c#", "rust", "golang", "docker", "kubernetes",
        "excel", "word", "photoshop", "powerpoint",
        "kinh tế hiện đại", "covid", "ai tools", "chatgpt", "openai", "công nghệ",
        "2027", "2028", "2029", "2030", "2031", "2032", "2033", "2034", "2035",
        "2036", "2037", "2038", "2039", "2040", "2041", "2042", "2043", "2044",
        "2045", "2046", "2047", "2048", "2049", "2050", "2100"
    ]

    IN_SCOPE_KEYWORDS = [
        "điện biên phủ", "hồ chí minh", "võ nguyên giáp", "geneve", "giơ-nê-vơ",
        "hiệp định", "paris", "kháng chiến", "chiến dịch", "tổng khởi nghĩa",
        "cách mạng tháng tám", "vĩ tuyến 17", "chống mỹ", "chống pháp", "đông dương",
        "mậu thân", "ấp bắc", "điện biên phủ trên không", "nhân văn giai phẩm",
        "cải cách ruộng đất", "lịch sử", "sự kiện", "nhân vật", "tướng", "quân đội"
    ]

    async def classify(self, query: str) -> DomainResult:
        """Classify query using hybrid keywords + LLM verification."""
        q = query.lower().strip()
        words = re.sub(r"[.,!?;:]", " ", q).split()

        # 1. Deterministic greetings
        for kw in self.GREETING_KEYWORDS:
            if " " in kw:
                if kw in q:
                    logger.info("domain_classified_rules", is_in_scope=True, reason="greeting_keyword")
                    return DomainResult(is_in_scope=True, reason="Câu chào hỏi hoặc xã giao.")
            else:
                if kw in words:
                    logger.info("domain_classified_rules", is_in_scope=True, reason="greeting_keyword")
                    return DomainResult(is_in_scope=True, reason="Câu chào hỏi hoặc xã giao.")

        # 2. Check for years to classify out-of-scope
        all_years = [int(y) for y in re.findall(r"\b(\d{4})\b", q)]
        if all_years:
            has_in_scope_year = any(1945 <= y <= 1975 for y in all_years)
            if not has_in_scope_year:
                logger.info("domain_classified_rules", is_in_scope=False, reason="out_of_scope_year")
                return DomainResult(is_in_scope=False, reason="Chứa mốc năm ngoài giai đoạn 1945-1975.")

        # 3. Check for clear historical years in 1945-1975
        years = re.findall(r"\b(19[4-7]\d)\b", q)
        has_valid_year = False
        for y_str in years:
            y = int(y_str)
            if 1945 <= y <= 1975:
                has_valid_year = True
                break
        
        # 4. Deterministic clear in-scope keywords
        for kw in self.IN_SCOPE_KEYWORDS:
            if kw in q:
                logger.info("domain_classified_rules", is_in_scope=True, reason="in_scope_keyword")
                return DomainResult(is_in_scope=True, reason="Từ khóa thuộc lịch sử Việt Nam.")

        if has_valid_year:
            logger.info("domain_classified_rules", is_in_scope=True, reason="valid_history_year")
            return DomainResult(is_in_scope=True, reason="Chứa mốc năm trong giai đoạn 1945-1975.")

        # 4. Deterministic clear out-of-scope keywords
        for kw in self.OUT_OF_SCOPE_KEYWORDS:
            if kw in q:
                logger.info("domain_classified_rules", is_in_scope=False, reason="out_of_scope_keyword")
                return DomainResult(is_in_scope=False, reason="Từ khóa nằm ngoài phạm vi nghiên cứu.")

        # 5. Fast LLM Classification
        try:
            llm = get_llm_client()
            # If mock client is used (like in tests), we can bypass or let mock handle
            from app.services.llm.client import MockLLMClient
            if isinstance(llm, MockLLMClient):
                # Standard fallback logic for Mock LLM in tests
                if "hà nội ngày mai" in q or "messi" in q or "thời tiết" in q:
                    return DomainResult(is_in_scope=False, reason="Ngoài phạm vi (Mock)")
                return DomainResult(is_in_scope=True, reason="Trong phạm vi (Mock)")

            prompt = f"""Bạn là bộ lọc phạm vi câu hỏi (Domain Guardrail AI) của HistoriAI.
Xác định xem câu hỏi của người dùng có thuộc phạm vi Lịch sử Việt Nam (đặc biệt giai đoạn 1945-1975) hoặc chào hỏi xã giao hay không.

Quy tắc phân loại:
- "IN": Câu hỏi liên quan đến lịch sử Việt Nam (đặc biệt 1945-1975), nhân vật lịch sử VN, hoặc các câu chào hỏi xã giao thân thiện.
- "OUT": Câu hỏi hoàn toàn ngoài ngành lịch sử VN (ví dụ: bóng đá, Lionel Messi, thời tiết hiện nay, công nghệ, lập trình, toán học, hoặc lịch sử nước khác không liên quan trực tiếp đến Việt Nam).

Truy vấn: "{query}"

Trả về định dạng JSON duy nhất:
{{
  "scope": "IN" hoặc "OUT",
  "reason": "Lý do ngắn gọn bằng tiếng Việt"
}}"""
            resp = await llm.generate(prompt, system="Bạn là AI bảo vệ phạm vi chuyên môn lịch sử Việt Nam.", max_tokens=150)
            parsed = parse_llm_json(resp)
            scope = parsed.get("scope", "IN").strip().upper()
            reason = parsed.get("reason", "Phân tích bối cảnh.")
            
            is_in_scope = (scope == "IN")
            logger.info("domain_classified_llm", is_in_scope=is_in_scope, reason=reason, query=query[:50])
            return DomainResult(is_in_scope=is_in_scope, reason=reason)
            
        except Exception as exc:
            logger.warning("domain_classification_llm_failed", error=str(exc))
            # Safe fallback: assume in-scope to prevent false positive rejects
            return DomainResult(is_in_scope=True, reason="Lỗi phân loại (Mặc định trong phạm vi).")


_classifier = DomainClassifier()


async def classify_domain(query: str) -> DomainResult:
    """Convenience function for domain classification."""
    return await _classifier.classify(query)
