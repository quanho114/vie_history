"""Historical Temporal Extractor.

Replaces the hardcoded 1940-2000 regex in TaskPlanner with a robust
extractor that handles:
  - Named Vietnamese dynasties  (nhà Trần, triều Lý, thời Tây Sơn…)
  - Century references            (thế kỷ XV, thế kỷ 18)
  - Explicit year literals        (938, 1428, 1954-1975)

Priority (first match wins): dynasty → century → explicit years.
"""

from __future__ import annotations

import re
from typing import TypedDict


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

class TemporalResult(TypedDict):
    """Temporal extraction result returned by HistoricalTemporalExtractor."""

    start_year: int | None
    end_year: int | None
    period: str | None
    dynasty: str | None


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

DYNASTY_MAP: dict[str, tuple[int, int]] = {
    "Ngô": (939, 967),
    "Đinh": (968, 980),
    "Tiền Lê": (980, 1009),
    "Lý": (1009, 1225),
    "Trần": (1225, 1400),
    "Hồ": (1400, 1407),
    "Hậu Lê": (1428, 1789),
    "Lê sơ": (1428, 1527),
    "Lê trung hưng": (1533, 1789),
    "Tây Sơn": (1778, 1802),
    "Nguyễn": (1802, 1945),
}

ROMAN_NUMERALS: dict[str, int] = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
    "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
    "XI": 11, "XII": 12, "XIII": 13, "XIV": 14, "XV": 15,
    "XVI": 16, "XVII": 17, "XVIII": 18, "XIX": 19, "XX": 20,
}

# Build a pattern that matches "nhà X", "triều X", or "thời X"
# where X is one of the dynasty keys.  Sorted longest-first to avoid
# partial matches (e.g. "Lê" before "Hậu Lê").
_DYNASTY_TRIGGERS = sorted(DYNASTY_MAP.keys(), key=len, reverse=True)

# Pre-compile century pattern: "thế kỷ" followed by Roman or Arabic numeral
_CENTURY_RE = re.compile(
    r"th\u1ebf\s+k\u1ef7\s+([IVXLCDM]{1,8}|\d{1,2})",
    re.IGNORECASE,
)

# Match 3-4 digit numbers that look like historical years (100–2099)
_YEAR_RE = re.compile(r"\b([1-9]\d{2,3})\b")


# ---------------------------------------------------------------------------
# Main extractor
# ---------------------------------------------------------------------------

class HistoricalTemporalExtractor:
    """Extract temporal metadata from a Vietnamese historical query string."""

    def extract(self, query: str) -> TemporalResult:
        """Return a :class:`TemporalResult` for *query*.

        Never raises; always returns a fully-typed dict (values may be None).
        """
        result: TemporalResult = {
            "start_year": None,
            "end_year": None,
            "period": None,
            "dynasty": None,
        }

        # --- Priority 1: named dynasty ----------------------------------
        dynasty_match = self._match_dynasty(query)
        if dynasty_match:
            name, (start, end) = dynasty_match
            result["dynasty"] = name
            result["start_year"] = start
            result["end_year"] = end
            return result

        # --- Priority 2: century expression ----------------------------
        century_match = _CENTURY_RE.search(query)
        if century_match:
            century_num = self._parse_century(century_match.group(1))
            if century_num is not None:
                result["start_year"] = (century_num - 1) * 100
                result["end_year"] = century_num * 100 - 1
                result["period"] = f"Thế kỷ {century_num}"
                return result

        # --- Priority 3: explicit year numbers -------------------------
        years = [
            int(y)
            for y in _YEAR_RE.findall(query)
            if 100 <= int(y) <= 2099
        ]
        if len(years) >= 2:
            result["start_year"] = min(years)
            result["end_year"] = max(years)
        elif len(years) == 1:
            result["start_year"] = years[0]
            result["end_year"] = years[0]
            # Auto-tag dynasty when year falls in a single dynasty window
            result["dynasty"] = self._dynasty_for_year(years[0])

        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _match_dynasty(
        self, query: str
    ) -> tuple[str, tuple[int, int]] | None:
        """Return *(dynasty_name, (start, end))* for the first dynasty hit."""
        q_lower = query.lower()
        for dynasty in _DYNASTY_TRIGGERS:
            d_lower = dynasty.lower()
            triggers = (
                f"nhà {d_lower}",
                f"triều {d_lower}",
                f"thời {d_lower}",
            )
            if any(t in q_lower for t in triggers):
                return dynasty, DYNASTY_MAP[dynasty]
        return None

    @staticmethod
    def _parse_century(token: str) -> int | None:
        """Convert Roman or Arabic numeral string to an integer century number."""
        upper = token.upper()
        if upper in ROMAN_NUMERALS:
            return ROMAN_NUMERALS[upper]
        try:
            val = int(token)
            return val if 1 <= val <= 20 else None
        except ValueError:
            return None

    @staticmethod
    def _dynasty_for_year(year: int) -> str | None:
        """Return the canonical dynasty name that covers *year*, or None."""
        # Use longest-first order to prefer specific entries
        for dynasty in _DYNASTY_TRIGGERS:
            start, end = DYNASTY_MAP[dynasty]
            if start <= year <= end:
                return dynasty
        # Special case: 938 is the Bạch Đằng battle — boundary of Ngô dynasty
        if year == 938:
            return "Ngô"
        return None
