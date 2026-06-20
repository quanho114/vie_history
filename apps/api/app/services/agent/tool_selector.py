class ToolSelector:
    def select_tools(self, query: str) -> list[str]:
        q = query.lower()
        selected = []
        if any(w in q for w in ["quan hệ", "dòng dõi", "vua", "gia phả", "cha con"]):
            selected.append("neo4j")
        if any(w in q for w in ["năm", "thế kỷ", "trước khi", "sau khi", "mốc thời gian"]):
            selected.append("timeline")
        if not selected or any(w in q for w in ["tóm tắt", "tại sao", "như thế nào"]):
            selected.append("vector")
        return selected
