"""Deterministic query expansion for Vietnamese historical aliases."""

from pathlib import Path
import json


class QueryExpander:
    """Expand queries using local alias dictionaries."""

    def __init__(self, alias_path: Path | None = None) -> None:
        repo_root = Path(__file__).resolve().parents[4]
        self.alias_path = alias_path or repo_root / "data" / "entity_aliases.json"
        self.aliases = self._load_aliases()

    def expand(self, query: str) -> list[str]:
        variants = [query]
        query_lower = query.lower()
        for canonical, aliases in self.aliases.items():
            terms = [canonical, *aliases]
            if any(term.lower() in query_lower for term in terms):
                expanded = query
                for term in terms:
                    if term.lower() not in expanded.lower():
                        expanded = f"{expanded} {term}"
                variants.append(expanded)
        return list(dict.fromkeys(variants))[:3]

    def _load_aliases(self) -> dict[str, list[str]]:
        if not self.alias_path.exists():
            return {}
        data = json.loads(self.alias_path.read_text(encoding="utf-8"))
        return {
            str(key): [str(item) for item in value]
            for key, value in data.items()
            if isinstance(value, list)
        }
