"""Query Metadata Extractor."""

import json
import httpx
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("query_metadata_extractor")

DYNASTY_KEYWORDS = {
    "Hồ": ["nhà hồ", "hồ quý ly", "hồ hán thương"],
    "Nguyễn": ["nhà nguyễn", "triều nguyễn", "gia long", "minh mạng", "tự đức", "khải định", "thiệu trị", "đồng khánh", "bảo đại"],
    "Lê": ["nhà lê", "triều lê", "lê lợi", "hậu lê", "tiền lê", "lê thánh tông"],
    "Trần": ["nhà trần", "triều trần", "trần hưng đạo", "trần nhân tông", "trần thái tông"],
    "Lý": ["nhà lý", "triều lý", "lý thái tổ", "lý thường kiệt", "lý thái tông"],
    "Tây Sơn": ["tây sơn", "quang trung", "nguyễn huệ"]
}

async def extract_query_metadata(query: str, api_key: str = None) -> dict:
    """
    Extract target historical metadata from a user query.
    Uses rules first, then falls back to Claude Haiku asynchronously.
    """
    q = query.lower()
    dynasty = None
    
    # Tier 1: Rules
    for dyn, keywords in DYNASTY_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            dynasty = dyn
            break
            
    # Tier 2: Asynchronous LLM Fallback
    if not dynasty:
        key = api_key or settings.ANTHROPIC_API_KEY
        if key:
            headers = {
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            payload = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 100,
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Extract the target historical dynasty (Lý, Trần, Lê, Hồ, Tây Sơn, Nguyễn) "
                            f"from this Vietnamese query. Return JSON only with key 'dynasty'. Query: {query}"
                        )
                    }
                ],
                "temperature": 0.0
            }
            try:
                async with httpx.AsyncClient() as client:
                    res = await client.post(
                        "https://api.anthropic.com/v1/messages",
                        json=payload,
                        headers=headers,
                        timeout=3.0
                    )
                    if res.status_code == 200:
                        content_text = res.json()["content"][0]["text"]
                        # Strip code fence blocks if any
                        if "```json" in content_text:
                            content_text = content_text.split("```json")[1].split("```")[0].strip()
                        elif "```" in content_text:
                            content_text = content_text.split("```")[1].split("```")[0].strip()
                        dynasty = json.loads(content_text.strip()).get("dynasty")
            except Exception as exc:
                logger.warning("query_llm_metadata_extraction_failed", error=str(exc))
        else:
            logger.debug("no_api_key_for_query_metadata_extraction")

    return {"dynasty": dynasty}
