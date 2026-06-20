HISTORICAL_ALIASES = {
    "quang trung": ["Nguyễn Huệ", "Bắc Bình Vương", "nhà Tây Sơn"],
    "nguyễn huệ": ["Quang Trung", "Bắc Bình Vương", "tây sơn tam kiệt"],
    "gia long": ["Nguyễn Ánh", "Nguyễn Vương", "Gia Long đế"],
    "nguyễn ánh": ["Gia Long", "Nguyễn Vương"],
    "nguyễn trãi": ["Ức Trai", "Lam Sơn khởi nghĩa"],
    "hồ chí minh": ["Nguyễn Ái Quốc", "Bác Hồ", "Nguyễn Tất Thành"]
}

class QueryExpansionAgent:
    def expand(self, query: str) -> str:
        q_lower = query.lower()
        expanded_terms = [query]
        for key, aliases in HISTORICAL_ALIASES.items():
            if key in q_lower:
                expanded_terms.extend(aliases)
        return " OR ".join(list(dict.fromkeys(expanded_terms)))
