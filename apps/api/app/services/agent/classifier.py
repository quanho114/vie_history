"""Intent Classifier service."""

import json
from dataclasses import dataclass, field

from app.core.logging import get_logger

logger = get_logger("intent_classifier")


@dataclass
class ClassificationResult:
    """Structured output from intent classification."""

    intent: str
    routing_hints: dict = field(default_factory=dict)
    entities: list[str] = field(default_factory=list)

    # ---------------------------------------------------------------------------
    # Convenience: default routing hints per intent so callers always get a dict
    # ---------------------------------------------------------------------------
    def __post_init__(self) -> None:
        defaults = _default_routing_hints(self.intent)
        # Only fill keys that are absent so LLM-provided hints take precedence
        for key, value in defaults.items():
            self.routing_hints.setdefault(key, value)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.intent == other
        if isinstance(other, ClassificationResult):
            return (
                self.intent == other.intent
                and self.routing_hints == other.routing_hints
                and self.entities == other.entities
            )
        return False


def _default_routing_hints(intent: str) -> dict:
    """Return sensible default routing hints based on intent alone."""
    base = {"use_wiki": False, "use_timeline": False, "use_graph": False, "use_vector": True}
    overrides: dict[str, dict] = {
        "factual":      {"use_wiki": True,  "use_timeline": False, "use_graph": False, "use_vector": True},
        "timeline":     {"use_wiki": False, "use_timeline": True,  "use_graph": False, "use_vector": True},
        "compare":      {"use_wiki": True,  "use_timeline": False, "use_graph": True,  "use_vector": True},
        "summary":      {"use_wiki": True,  "use_timeline": True,  "use_graph": False, "use_vector": True},
        "source_audit": {"use_wiki": False, "use_timeline": False, "use_graph": False, "use_vector": True},
        "cause_effect": {"use_wiki": True,  "use_timeline": False, "use_graph": True,  "use_vector": True},
        "multi_hop":    {"use_wiki": True,  "use_timeline": True,  "use_graph": True,  "use_vector": True},
        "source_check": {"use_wiki": False, "use_timeline": False, "use_graph": False, "use_vector": True},
        "out_of_scope": {"use_wiki": False, "use_timeline": False, "use_graph": False, "use_vector": False},
    }
    return overrides.get(intent, base)


class IntentClassifier:
    """
    Classifies user queries into intent categories.

    Intent classes:
    - factual:      Direct fact lookup (who, when, where)
    - timeline:     Chronological event lookup
    - compare:      Comparison between two subjects
    - summary:      Topic/event summary
    - source_audit: Find sources for a topic
    - cause_effect: Causal chain analysis (nguyên nhân / hệ quả)
    - multi_hop:    Multi-step reasoning across events/people
    - source_check: Verify or cross-check a specific claim/source
    - out_of_scope: Outside 1945-1975 Vietnam history domain
    """

    INTENTS = [
        "factual",
        "timeline",
        "compare",
        "summary",
        "source_audit",
        "cause_effect",
        "multi_hop",
        "source_check",
        "out_of_scope",
    ]

    COMPARE_KEYWORDS = [
        "so sánh",
        "compare",
        "khác nhau",
        "giống nhau",
        "giữa",
        "và",
    ]

    TIMELINE_KEYWORDS = [
        "timeline",
        "lịch sử",
        "thời gian",
        "năm",
        "thập niên",
        "giai đoạn",
        "diễn biến",
        "trình tự",
        "theo thứ tự",
    ]

    SUMMARY_KEYWORDS = [
        "tóm tắt",
        "tổng hợp",
        "summary",
        "giới thiệu",
        "trình bày",
        "mô tả",
    ]

    SOURCE_AUDIT_KEYWORDS = [
        "tài liệu nào",
        "nguồn nào",
        "source",
        "tài liệu về",
        "viết về",
        "nói về",
    ]

    CAUSE_EFFECT_KEYWORDS = [
        "nguyên nhân",
        "hệ quả",
        "kết quả",
        "tại sao",
        "why",
        "cause",
        "effect",
        "dẫn đến",
        "vì sao",
        "ảnh hưởng",
    ]

    MULTI_HOP_KEYWORDS = [
        "liên quan",
        "kết nối",
        "mối liên hệ",
        "chuỗi sự kiện",
        "sau đó",
        "trước đó",
        "chain",
        "multi",
    ]

    SOURCE_CHECK_KEYWORDS = [
        "xác minh",
        "kiểm tra",
        "verify",
        "check",
        "đúng không",
        "có phải",
        "chính xác không",
    ]

    # Out-of-scope keywords that clearly indicate non-Vietnam-history queries.
    # Must cover future years beyond 2026 and clearly unrelated topics.
    OUT_OF_SCOPE_KEYWORDS = [
        # Future years beyond current year (2026)
        "2027", "2028", "2029", "2030", "2031", "2032", "2033", "2034", "2035",
        "2036", "2037", "2038", "2039", "2040", "2041", "2042", "2043", "2044",
        "2045", "2046", "2047", "2048", "2049", "2050", "2051", "2052", "2053",
        "2054", "2055", "2056", "2057", "2058", "2059", "2060", "2061", "2062",
        "2063", "2064", "2065", "2066", "2067", "2068", "2069", "2070", "2071",
        "2072", "2073", "2074", "2075", "2076", "2077", "2078", "2079", "2080",
        "2081", "2082", "2083", "2084", "2085", "2086", "2087", "2088", "2089",
        "2090", "2091", "2092", "2093", "2094", "2095", "2096", "2097", "2098",
        "2099", "2100", "2101", "2102", "2103", "2104", "2105", "2106", "2107",
        "2108", "2109", "2110",
    ]

    def __init__(self, llm_provider=None):
        self.llm_provider = llm_provider

    async def classify(self, query: str) -> ClassificationResult:
        """
        Classify query intent and produce routing hints + extracted entities.

        Falls back to keyword matching if no LLM provider is configured or
        if the LLM call fails.
        """
        # Run DomainClassifier check first to intercept out-of-scope queries
        from app.agents.domain_classifier import classify_domain
        domain_res = await classify_domain(query)
        if not domain_res.is_in_scope:
            logger.info("intent_classified_domain_guardrail", intent="out_of_scope", query=query[:50])
            return ClassificationResult(intent="out_of_scope")

        # Fast keyword path for clear-cut cases
        keyword_intent = self._classify_by_keywords(query)

        # Dynamically detect if an LLM client is available (either from dynamic headers or environment settings)
        has_llm = False
        try:
            from app.services.llm.client import get_llm_client
            get_llm_client()
            has_llm = True
        except Exception:
            pass

        # Use LLM for richer output (entities, routing_hints) or ambiguous cases
        if has_llm or self.llm_provider:
            llm_result = await self._classify_with_llm(query)
            if llm_result:
                return llm_result

        logger.info("intent_classified_by_keywords", intent=keyword_intent, query=query[:50])
        return ClassificationResult(intent=keyword_intent)

    def _classify_by_keywords(self, query: str) -> str:
        """Fast keyword-based classification. Returns intent string only."""
        query_lower = query.lower()

        # Out of scope first
        for keyword in self.OUT_OF_SCOPE_KEYWORDS:
            if keyword in query_lower:
                return "out_of_scope"

        # Cause / effect
        for kw in self.CAUSE_EFFECT_KEYWORDS:
            if kw in query_lower:
                return "cause_effect"

        # Source verification
        for kw in self.SOURCE_CHECK_KEYWORDS:
            if kw in query_lower:
                return "source_check"

        # Multi-hop
        for kw in self.MULTI_HOP_KEYWORDS:
            if kw in query_lower:
                return "multi_hop"

        # Compare
        compare_score = sum(1 for kw in self.COMPARE_KEYWORDS if kw in query_lower)
        if compare_score >= 2 or "so sánh" in query_lower or "compare" in query_lower:
            return "compare"

        # Timeline
        for kw in self.TIMELINE_KEYWORDS:
            if kw in query_lower:
                return "timeline"

        # Summary
        for kw in self.SUMMARY_KEYWORDS:
            if kw in query_lower:
                return "summary"

        # Source audit
        for kw in self.SOURCE_AUDIT_KEYWORDS:
            if kw in query_lower:
                return "source_audit"

        return "factual"

    async def _classify_with_llm(self, query: str) -> ClassificationResult | None:
        """
        Use LLM to classify intent and extract entities + routing hints.

        Expected JSON response::

            {
              "intent": "cause_effect",
              "entities": ["Chiến dịch Hồ Chí Minh", "Nguyễn Văn Thiệu"],
              "routing_hints": {
                "use_wiki": true,
                "use_timeline": false,
                "use_graph": true,
                "use_vector": true
              }
            }
        """
        prompt = f"""Bạn là trợ lý phân tích truy vấn lịch sử Việt Nam (1945-1975).

Phân loại câu hỏi sau vào một trong các intent:
- factual: Tra cứu sự kiện/nhân vật cụ thể (ai, khi nào, ở đâu)
- timeline: Chuỗi sự kiện theo thứ tự thời gian
- compare: So sánh hai đối tượng/giai đoạn
- summary: Tóm tắt tổng quan một chủ đề
- source_audit: Tìm tài liệu/nguồn về chủ đề
- cause_effect: Phân tích nguyên nhân và hệ quả
- multi_hop: Suy luận qua nhiều sự kiện hoặc nhân vật liên kết
- source_check: Xác minh hoặc kiểm tra tính chính xác của một tuyên bố
- out_of_scope: Ngoài phạm vi lịch sử Việt Nam 1945-1975

Truy vấn: {query}

Trả về JSON hợp lệ (không có markdown, không có giải thích):
{{
  "intent": "<intent>",
  "entities": ["<thực thể 1>", "<thực thể 2>"],
  "routing_hints": {{
    "use_wiki": <true/false>,
    "use_timeline": <true/false>,
    "use_graph": <true/false>,
    "use_vector": <true/false>
  }}
}}"""

        try:
            from app.services.llm.client import get_llm_client
            client = get_llm_client()
            response = await client.generate(prompt, max_tokens=256)

            # Strip markdown code fences if present
            text = response.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()

            data = json.loads(text)
            intent = data.get("intent", "").strip().lower()
            if intent not in self.INTENTS:
                logger.warning("llm_invalid_intent", intent=intent)
                intent = self._classify_by_keywords(query)

            entities: list[str] = [str(e) for e in data.get("entities", []) if e]
            routing_hints: dict = data.get("routing_hints", {})

            logger.info("llm_intent_classified", intent=intent, entities=entities, query=query[:50])
            return ClassificationResult(
                intent=intent,
                routing_hints=routing_hints,
                entities=entities,
            )

        except Exception as exc:
            logger.warning("llm_classification_failed", error=str(exc))
            return None
