"""Tests for retrieval helpers."""

from app.retrieval.query_expander import QueryExpander
from app.retrieval.reranker import LexicalReranker


def test_query_expander_includes_aliases(tmp_path) -> None:
    alias_path = tmp_path / "aliases.json"
    alias_path.write_text('{"Hồ Chí Minh": ["Nguyễn Ái Quốc"]}', encoding="utf-8")

    expanded = QueryExpander(alias_path=alias_path).expand("Vai trò của Nguyễn Ái Quốc")

    assert any("Hồ Chí Minh" in query for query in expanded)


def test_reranker_prefers_overlap() -> None:
    chunks = [
        {"content": "kinh tế xã hội", "score": 0.1},
        {"content": "Điện Biên Phủ năm 1954", "score": 0.1},
    ]

    ranked = LexicalReranker().rerank("Điện Biên Phủ", chunks)

    assert ranked[0]["content"] == "Điện Biên Phủ năm 1954"
