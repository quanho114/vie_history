"""Vietnamese Historical Search Utilities: Entity Normalization and Calendar Expansion."""

import re
import unicodedata

# Map of historical figure aliases to their group of normalized names
HISTORICAL_ALIASES = {
    "nguyen hue": ["Nguyễn Huệ", "Quang Trung", "Bắc Bình Vương", "Hồ Thơm"],
    "quang trung": ["Nguyễn Huệ", "Quang Trung", "Bắc Bình Vương", "Hồ Thơm"],
    "ho thom": ["Nguyễn Huệ", "Quang Trung", "Bắc Bình Vương", "Hồ Thơm"],
    "bac binh vuong": ["Nguyễn Huệ", "Quang Trung", "Bắc Bình Vương", "Hồ Thơm"],
    
    "ly thuong kiet": ["Lý Thường Kiệt", "Ngô Tuấn"],
    "ngo tuan": ["Lý Thường Kiệt", "Ngô Tuấn"],
    
    "tran hung dao": ["Trần Hưng Đạo", "Trần Quốc Tuấn", "Hưng Đạo Đại Vương"],
    "tran quoc tuan": ["Trần Hưng Đạo", "Trần Quốc Tuấn", "Hưng Đạo Đại Vương"],
    "hung dao dai vuong": ["Trần Hưng Đạo", "Trần Quốc Tuấn", "Hưng Đạo Đại Vương"],
    
    "ho chi minh": ["Hồ Chí Minh", "Nguyễn Ái Quốc", "Bác Hồ", "Nguyễn Tất Thành", "Nguyễn Sinh Cung"],
    "nguyen ai quoc": ["Hồ Chí Minh", "Nguyễn Ái Quốc", "Bác Hồ", "Nguyễn Tất Thành", "Nguyễn Sinh Cung"],
    "bac ho": ["Hồ Chí Minh", "Nguyễn Ái Quốc", "Bác Hồ", "Nguyễn Tất Thành", "Nguyễn Sinh Cung"],
    
    "vo nguyen giap": ["Võ Nguyên Giáp", "Đại tướng Võ Nguyên Giáp", "Anh Văn"],
    "anh van": ["Võ Nguyên Giáp", "Đại tướng Võ Nguyên Giáp", "Anh Văn"],
    
    "gia long": ["Gia Long", "Nguyễn Ánh"],
    "nguyen anh": ["Gia Long", "Nguyễn Ánh"]
}

# Known Can Chi historical years mapped to Solar year candidates
CAN_CHI_YEARS = {
    "ky dau": ["1789", "1909", "1969"],
    "mau than": ["1788", "1908", "1968"],
    "at dau": ["1945", "1885", "2005"],
    "canh ty": ["40", "1960", "2020"],
    "giap ngo": ["1954", "1894", "2014"],
    "binh than": ["1956", "1896", "2016"],
    "nham tuat": ["1802", "1982", "1922"],
    "giap thin": ["1964", "1904", "2024"],
    "dinh suu": ["1997", "1937"],
    "nham ty": ["1972", "1912"]
}


def normalize_vietnamese_text(text: str) -> str:
    """Lowercase and strip all Vietnamese diacritics / tone marks using unicodedata decomposition."""
    if not text:
        return ""
    # Normalize to NFD (Decomposition)
    nfd_form = unicodedata.normalize('NFD', text)
    # Remove combining diacritic marks (category 'Mn')
    cleaned = "".join([c for c in nfd_form if unicodedata.category(c) != 'Mn'])
    # Lowercase and convert specific characters like 'đ' -> 'd'
    t = cleaned.lower().strip()
    t = t.replace('đ', 'd')
    return t


def expand_historical_query(query: str) -> str:
    """
    Expand Vietnamese historical entity names and Can Chi calendar years to optimize search recall.
    
    Example:
      "Chiến dịch năm Mậu Thân của Nguyễn Huệ" ->
      "Chiến dịch năm Mậu Thân của Nguyễn Huệ (Quang Trung, Bắc Bình Vương, Hồ Thơm) (1788, 1908, 1968)"
    """
    if not query:
        return query
        
    expanded = query
    normalized_query = normalize_vietnamese_text(query)
    
    # 1. Expand historical entity aliases
    found_groups = []
    for alias_key, group in HISTORICAL_ALIASES.items():
        if alias_key in normalized_query:
            # Prevent duplicate group expansion
            if group not in found_groups:
                found_groups.append(group)
                # Filter out aliases already in the query
                new_aliases = [name for name in group if normalize_vietnamese_text(name) not in normalized_query]
                if new_aliases:
                    expanded += f" ({', '.join(new_aliases)})"
                    
    # 2. Expand Lunar Can Chi years to solar year candidates
    for can_chi, solar_years in CAN_CHI_YEARS.items():
        if can_chi in normalized_query:
            # Check if years are already written in query
            existing_years = [y for y in solar_years if y in query]
            if not existing_years:
                expanded += f" ({', '.join(solar_years)})"
                
    return expanded
