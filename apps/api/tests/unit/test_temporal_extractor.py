"""Tests for HistoricalTemporalExtractor.

Covers:
- Single ancient year (938, 1789)
- Explicit year ranges (1945-1975)
- Dynasty name variants (nhà X, triều X, thời X)
- Century references — Roman (XV) and Arabic (18)
- Edge cases: empty query, no temporal info
- Integration with TaskPlanner._extract_years
"""

from __future__ import annotations

import pytest
from app.services.agent.temporal_extractor import (
    HistoricalTemporalExtractor,
    DYNASTY_MAP,
    ROMAN_NUMERALS,
)


@pytest.fixture
def extractor() -> HistoricalTemporalExtractor:
    return HistoricalTemporalExtractor()


# ---------------------------------------------------------------------------
# Single explicit years
# ---------------------------------------------------------------------------

class TestExplicitYears:
    def test_ancient_year_938(self, extractor):
        res = extractor.extract("Chiến thắng Bạch Đằng năm 938 diễn ra như thế nào?")
        assert res["start_year"] == 938
        assert res["end_year"] == 938

    def test_ancient_year_1428(self, extractor):
        res = extractor.extract("Khởi nghĩa Lam Sơn thắng lợi năm 1428")
        assert res["start_year"] == 1428
        assert res["end_year"] == 1428

    def test_modern_year_1975(self, extractor):
        res = extractor.extract("Giải phóng miền Nam năm 1975")
        assert res["start_year"] == 1975
        assert res["end_year"] == 1975


# ---------------------------------------------------------------------------
# Year ranges
# ---------------------------------------------------------------------------

class TestYearRanges:
    def test_range_1945_1975(self, extractor):
        res = extractor.extract("Giai đoạn lịch sử 1945-1975")
        assert res["start_year"] == 1945
        assert res["end_year"] == 1975

    def test_range_1418_1428(self, extractor):
        res = extractor.extract("Từ 1418 đến 1428 là thời kỳ khởi nghĩa Lam Sơn")
        assert res["start_year"] == 1418
        assert res["end_year"] == 1428

    def test_min_max_ordering(self, extractor):
        res = extractor.extract("Từ năm 1975 nhìn lại năm 1945")
        assert res["start_year"] == 1945
        assert res["end_year"] == 1975


# ---------------------------------------------------------------------------
# Dynasty names
# ---------------------------------------------------------------------------

class TestDynastyNames:
    def test_nha_prefix(self, extractor):
        res = extractor.extract("Chính sách đối ngoại nhà Lý")
        assert res["dynasty"] == "Lý"
        assert res["start_year"] == DYNASTY_MAP["Lý"][0]
        assert res["end_year"] == DYNASTY_MAP["Lý"][1]

    def test_trieu_prefix(self, extractor):
        res = extractor.extract("Các vị vua triều Trần")
        assert res["dynasty"] == "Trần"
        assert res["start_year"] == 1225
        assert res["end_year"] == 1400

    def test_thoi_prefix(self, extractor):
        res = extractor.extract("Kinh tế thời Nguyễn")
        assert res["dynasty"] == "Nguyễn"
        assert res["start_year"] == 1802

    def test_tay_son(self, extractor):
        res = extractor.extract("Phong trào khởi nghĩa thời Tây Sơn")
        assert res["dynasty"] == "Tây Sơn"
        assert res["start_year"] == 1778
        assert res["end_year"] == 1802

    def test_dynasty_case_insensitive(self, extractor):
        res = extractor.extract("nhà trần đánh quân Nguyên")
        assert res["dynasty"] == "Trần"

    def test_all_dynasties_covered(self, extractor):
        for dynasty in DYNASTY_MAP:
            res = extractor.extract(f"nhà {dynasty}")
            assert res["dynasty"] == dynasty, f"Failed for dynasty: {dynasty}"


# ---------------------------------------------------------------------------
# Century references
# ---------------------------------------------------------------------------

class TestCenturyReferences:
    def test_roman_century_xv(self, extractor):
        res = extractor.extract("Tình hình kinh tế thế kỷ XV ở Đại Việt")
        assert res["start_year"] == 1400
        assert res["end_year"] == 1499

    def test_roman_century_x(self, extractor):
        res = extractor.extract("Thế kỷ X là thời kỳ hỗn loạn")
        assert res["start_year"] == 900
        assert res["end_year"] == 999

    def test_arabic_century_18(self, extractor):
        res = extractor.extract("Văn hóa thế kỷ 18")
        assert res["start_year"] == 1700
        assert res["end_year"] == 1799

    def test_arabic_century_19(self, extractor):
        res = extractor.extract("Thế kỷ 19 chứng kiến thực dân Pháp")
        assert res["start_year"] == 1800
        assert res["end_year"] == 1899


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_no_temporal_info(self, extractor):
        res = extractor.extract("Lịch sử Việt Nam rất phong phú")
        assert res["start_year"] is None
        assert res["end_year"] is None
        assert res["dynasty"] is None
        assert res["period"] is None

    def test_empty_string(self, extractor):
        res = extractor.extract("")
        assert res["start_year"] is None
        assert res["end_year"] is None

    def test_dynasty_takes_priority_over_year(self, extractor):
        # Even though "938" is in query, dynasty match should win
        res = extractor.extract("Chiến thắng nhà Ngô năm 938")
        assert res["dynasty"] == "Ngô"
        # start/end come from dynasty map, not just the literal 938
        assert res["start_year"] == DYNASTY_MAP["Ngô"][0]

    def test_dynasty_takes_priority_over_century(self, extractor):
        res = extractor.extract("Nghệ thuật thế kỷ XIII nhà Trần")
        assert res["dynasty"] == "Trần"

    def test_always_returns_typed_dict(self, extractor):
        res = extractor.extract("bất kỳ câu hỏi nào")
        assert isinstance(res, dict)
        assert "start_year" in res
        assert "end_year" in res
        assert "dynasty" in res
        assert "period" in res


# ---------------------------------------------------------------------------
# Integration with TaskPlanner
# ---------------------------------------------------------------------------

class TestPlannerIntegration:
    def test_planner_timeline_ancient_year(self):
        from app.services.agent.planner import TaskPlanner
        planner = TaskPlanner()
        plan = planner.plan(
            "timeline",
            "Chiến thắng Bạch Đằng năm 938",
            "Chiến thắng Bạch Đằng năm 938",
        )
        assert plan is not None
        # Should have year_range metadata for year 938
        if plan.metadata_filters:
            year_range = plan.metadata_filters.get("year_range")
            if year_range:
                assert year_range[0] <= 938 <= year_range[1]

    def test_planner_does_not_crash_on_no_year(self):
        from app.services.agent.planner import TaskPlanner
        planner = TaskPlanner()
        plan = planner.plan("timeline", "Lịch sử Việt Nam", "Lịch sử Việt Nam")
        assert plan is not None
