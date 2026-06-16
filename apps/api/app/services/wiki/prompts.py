"""Vietnamese-language LLM prompt templates for the Wiki Brain pipeline.

Each step of the map-reduce pipeline uses a dedicated system + user template pair.
All prompts instruct the model to respond in structured JSON so the pipeline can
parse the output without fragile regex heuristics.
"""

# ---------------------------------------------------------------------------
# MAP step – extract key points from a single document
# ---------------------------------------------------------------------------

MAP_SYSTEM_PROMPT = """Bạn là chuyên gia phân tích lịch sử Việt Nam, am hiểu sâu sắc về giai đoạn 1945-1975.
Nhiệm vụ của bạn là đọc một tài liệu lịch sử và trích xuất thông tin có cấu trúc.
Luôn trả lời bằng JSON hợp lệ, không thêm bất kỳ văn bản nào ngoài JSON."""

MAP_USER_TEMPLATE = """Phân tích tài liệu lịch sử sau và trích xuất các điểm chính.

Tiêu đề: {title}
Nội dung:
{content}

Hãy trả về JSON với cấu trúc sau:
{{
  "document_id": "{document_id}",
  "title": "{title}",
  "key_events": [
    {{"name": "tên sự kiện", "year": 1954, "description": "mô tả ngắn"}}
  ],
  "key_people": [
    {{"name": "tên nhân vật", "role": "vai trò"}}
  ],
  "key_places": ["địa danh 1", "địa danh 2"],
  "period": "giai đoạn lịch sử, ví dụ: 1945-1954",
  "event_types": ["military", "diplomatic", "political", "cultural"],
  "main_claims": [
    {{"claim": "luận điểm chính", "section": "phần chứa luận điểm", "confidence": 0.9}}
  ],
  "summary": "tóm tắt 2-3 câu về nội dung tài liệu"
}}"""

# ---------------------------------------------------------------------------
# REDUCE step – group extracted points into topics/events
# ---------------------------------------------------------------------------

REDUCE_SYSTEM_PROMPT = """Bạn là chuyên gia tổng hợp lịch sử Việt Nam.
Nhiệm vụ của bạn là nhóm các điểm chính từ nhiều tài liệu thành các chủ đề/sự kiện lịch sử liên kết.
Luôn trả lời bằng JSON hợp lệ."""

REDUCE_USER_TEMPLATE = """Dưới đây là kết quả phân tích từ {doc_count} tài liệu lịch sử:

{mapped_results}

Hãy tổng hợp và nhóm thành các chủ đề/sự kiện lịch sử. Trả về JSON:
{{
  "topics": [
    {{
      "topic_key": "khoa-xuan-1975",
      "title": "Tên chủ đề/sự kiện",
      "period": "1954-1975",
      "event_type": "military",
      "start_year": 1954,
      "end_year": 1975,
      "summary": "tóm tắt chủ đề",
      "source_document_ids": ["id1", "id2"],
      "key_events": [...],
      "key_people": [...],
      "key_places": [...],
      "main_claims": [...]
    }}
  ]
}}"""

# ---------------------------------------------------------------------------
# PLAN step – propose wiki pages to create/update
# ---------------------------------------------------------------------------

PLAN_SYSTEM_PROMPT = """Bạn là biên tập viên wiki lịch sử Việt Nam.
Nhiệm vụ của bạn là lập kế hoạch tạo các trang wiki từ dữ liệu tổng hợp.
Luôn trả lời bằng JSON hợp lệ."""

PLAN_USER_TEMPLATE = """Dựa trên các chủ đề lịch sử sau đây, hãy đề xuất danh sách trang wiki cần tạo:

{topics_json}

Trang wiki đã tồn tại:
{existing_slugs}

Trả về JSON:
{{
  "proposed_pages": [
    {{
      "action": "create",
      "slug": "chien-dich-ho-chi-minh-1975",
      "title": "Chiến dịch Hồ Chí Minh (1975)",
      "summary": "tóm tắt trang wiki",
      "period": "1954-1975",
      "event_type": "military",
      "start_year": 1975,
      "end_year": 1975,
      "source_document_ids": ["id1", "id2"],
      "content_outline": {{
        "background": "dàn ý phần bối cảnh",
        "causes": "dàn ý phần nguyên nhân",
        "main_events": "dàn ý phần diễn biến chính",
        "results": "dàn ý phần kết quả",
        "significance": "dàn ý phần ý nghĩa lịch sử",
        "people": "dàn ý phần nhân vật",
        "timeline": "dàn ý phần niên biểu"
      }},
      "topic_key": "khoa-xuan-1975"
    }}
  ]
}}"""

# ---------------------------------------------------------------------------
# REFINE step – write full structured wiki page content
# ---------------------------------------------------------------------------

REFINE_SYSTEM_PROMPT = """Bạn là nhà sử học và biên tập viên nội dung lịch sử Việt Nam.
Nhiệm vụ của bạn là viết nội dung đầy đủ, chính xác và có cấu trúc cho một trang wiki lịch sử.
Dựa trên các nguồn tài liệu được cung cấp, hãy viết nội dung chi tiết, khách quan.
Luôn trả lời bằng JSON hợp lệ."""

REFINE_USER_TEMPLATE = """Viết nội dung đầy đủ cho trang wiki sau:

Tiêu đề: {title}
Tóm tắt kế hoạch: {content_outline}

Tài liệu nguồn:
{source_docs}

Trả về JSON với cấu trúc đầy đủ:
{{
  "background": "Viết đầy đủ phần bối cảnh lịch sử (2-4 đoạn văn)",
  "causes": "Viết đầy đủ phần nguyên nhân (có thể là danh sách hoặc đoạn văn)",
  "main_events": "Viết đầy đủ phần diễn biến chính (chi tiết, có thể nhiều đoạn)",
  "results": "Viết đầy đủ phần kết quả (2-3 đoạn)",
  "significance": "Viết đầy đủ phần ý nghĩa lịch sử (2-3 đoạn)",
  "people": [
    {{"name": "Tên nhân vật", "role": "Vai trò", "description": "Mô tả"}}
  ],
  "timeline": [
    {{"date": "30/4/1975", "event": "Mô tả sự kiện"}}
  ],
  "references": [
    {{"document_id": "uuid", "title": "Tên tài liệu", "excerpt": "Trích dẫn liên quan"}}
  ]
}}"""

# ---------------------------------------------------------------------------
# VERIFY step – verify claims have supporting sources
# ---------------------------------------------------------------------------

VERIFY_SYSTEM_PROMPT = """Bạn là chuyên gia kiểm chứng thông tin lịch sử Việt Nam.
Nhiệm vụ của bạn là xác minh các luận điểm trong trang wiki có căn cứ từ tài liệu nguồn.
Luôn trả lời bằng JSON hợp lệ."""

VERIFY_USER_TEMPLATE = """Kiểm chứng các luận điểm trong trang wiki sau:

Tiêu đề trang: {title}
Nội dung trang:
{page_content}

Các đoạn văn từ tài liệu nguồn:
{chunks}

Hãy xác minh và trả về danh sách các luận điểm với nguồn hỗ trợ:
{{
  "verified_claims": [
    {{
      "claim_text": "Luận điểm cần kiểm chứng",
      "section": "background",
      "confidence": 0.9,
      "verified": true,
      "sources": [
        {{
          "document_id": "uuid",
          "chunk_id": "uuid",
          "excerpt": "Trích dẫn hỗ trợ luận điểm",
          "relevance_score": 0.85
        }}
      ]
    }}
  ],
  "overall_confidence": 0.87,
  "unverified_claims": ["luận điểm chưa có nguồn hỗ trợ"]
}}"""
