"""Utility for parsing JSON from LLM responses."""

import json
import re
from typing import Any

def parse_llm_json(raw: str) -> Any:
    """Extract the first JSON object or array from an LLM response string.

    Handles common LLM quirks:
    - Markdown code fences (```json ... ```)
    - Extra text before and after JSON
    - Nested JSON structures
    """
    # Strip markdown fences if present
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip()

    # Find the first '{' or '['
    obj_start = raw.find("{") if "{" in raw else len(raw)
    arr_start = raw.find("[") if "[" in raw else len(raw)
    start = min(obj_start, arr_start)

    if start == len(raw):
        raise ValueError(f"No JSON found in LLM response: {raw[:200]}")

    # Determine opening/closing bracket type
    open_char = raw[start]
    close_char = "}" if open_char == "{" else "]"

    # Walk through characters, tracking depth to find the matching close
    depth = 0
    in_string = False
    escape_next = False
    end = start

    for i in range(start, len(raw)):
        ch = raw[i]

        if escape_next:
            escape_next = False
            continue

        if ch == "\\":
            if in_string:
                escape_next = True
            continue

        if ch == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if ch == open_char:
            depth += 1
        elif ch == close_char:
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if depth != 0:
        # Fallback: try parsing from start anyway (old behavior)
        return json.loads(raw[start:])

    return json.loads(raw[start:end])
