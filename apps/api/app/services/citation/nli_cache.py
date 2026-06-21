import os
import sqlite3
import hashlib
import threading
from typing import Optional

class NLICache:
    """Persistent SQLite-backed cache for NLI premise/hypothesis verification scores."""
    
    def __init__(self, cache_file_path: str = "data/nli_cache.db") -> None:
        self.cache_file_path = cache_file_path
        # Ensure target directory exists
        dir_name = os.path.dirname(self.cache_file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        with self._lock:
            conn = sqlite3.connect(self.cache_file_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nli_cache (
                    key TEXT PRIMARY KEY,
                    score REAL
                )
            """)
            conn.commit()
            conn.close()

    def _get_key(self, premise: str, hypothesis: str) -> str:
        data = f"{premise.strip()}|||{hypothesis.strip()}"
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def get(self, premise: str, hypothesis: str) -> Optional[float]:
        key = self._get_key(premise, hypothesis)
        with self._lock:
            conn = sqlite3.connect(self.cache_file_path)
            cursor = conn.cursor()
            cursor.execute("SELECT score FROM nli_cache WHERE key = ?", (key,))
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else None

    def set(self, premise: str, hypothesis: str, score: float) -> None:
        key = self._get_key(premise, hypothesis)
        with self._lock:
            conn = sqlite3.connect(self.cache_file_path)
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO nli_cache (key, score) VALUES (?, ?)", (key, score))
            conn.commit()
            conn.close()
