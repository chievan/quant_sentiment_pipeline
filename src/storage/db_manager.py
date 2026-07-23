import sqlite3
import os
import hashlib
from typing import List, Dict, Any, Optional

class NewsDBManager:
    def __init__(self, db_path: str = "data/quant_news.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Initialize SQLite table structure if not present."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hash_id TEXT UNIQUE,
                    title TEXT NOT NULL,
                    source_channel TEXT,
                    source_name TEXT,
                    pub_date TEXT,
                    url TEXT,
                    ai_brief TEXT,
                    content TEXT,
                    sentiment_score REAL DEFAULT 0.0,
                    fof_strategy TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_hash ON articles(hash_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pub_date ON articles(pub_date);")
            conn.commit()

    @staticmethod
    def generate_hash(title: str, url: str) -> str:
        """Generate MD5 hash ID for deduplication based on title and URL."""
        raw = f"{title.strip()}_{url.strip()}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def upsert_article(self, article: Dict[str, Any]) -> bool:
        """Inserts or updates an article in SQLite database."""
        hash_id = self.generate_hash(article["title"], article.get("link", ""))
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO articles (
                        hash_id, title, source_channel, source_name, pub_date, url, ai_brief, content, sentiment_score, fof_strategy
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(hash_id) DO UPDATE SET
                        ai_brief = excluded.ai_brief,
                        content = excluded.content,
                        sentiment_score = excluded.sentiment_score,
                        fof_strategy = excluded.fof_strategy
                """, (
                    hash_id,
                    article.get("title", ""),
                    article.get("source_channel", "网络资讯"),
                    article.get("source_name", article.get("source", "")),
                    article.get("pubDate", ""),
                    article.get("link", ""),
                    article.get("ai_brief", ""),
                    article.get("content", article.get("summary", "")),
                    float(article.get("sentiment_score", 0.0)),
                    article.get("fof_strategy", "")
                ))
                conn.commit()
                return True
            except Exception as e:
                print(f"[NewsDBManager] DB Error: {e}")
                return False

    def upsert_batch(self, articles: List[Dict[str, Any]]) -> int:
        """Batch inserts or updates articles."""
        count = 0
        for item in articles:
            if self.upsert_article(item):
                count += 1
        return count

    def get_latest_articles(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch latest records from SQLite."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM articles ORDER BY created_at DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
