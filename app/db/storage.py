import json
import sqlite3
from pathlib import Path
from typing import Optional

from app.Schema.review import syntax


DB_PATH = Path(__file__).resolve().parent.parent.parent / "reviews.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            review_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            overall_score INTEGER NOT NULL,
            summary TEXT NOT NULL,
            issues_json TEXT NOT NULL,
            metrics_json TEXT NOT NULL,
            submitted_code TEXT NOT NULL,
            source TEXT DEFAULT 'review',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Migration: Add source column if it doesn't exist
    cursor.execute("PRAGMA table_info(reviews)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'source' not in columns:
        cursor.execute("ALTER TABLE reviews ADD COLUMN source TEXT DEFAULT 'review'")

    conn.commit()
    conn.close()


def save_review(submitted_code: str, review: syntax, source: str = "review") -> None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO reviews (
            review_id,
            status,
            overall_score,
            summary,
            issues_json,
            metrics_json,
            submitted_code,
            source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        review.review_id,
        review.status.value if hasattr(review.status, "value") else review.status,
        review.overall_score,
        review.summary,
        json.dumps([issue.model_dump() for issue in review.issues]),
        json.dumps(review.metrics.model_dump()),
        submitted_code,
        source
    ))

    conn.commit()
    conn.close()


def get_review_by_id(review_id: str) -> Optional[sqlite3.Row]:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM reviews WHERE review_id = ?", (review_id,))
    row = cursor.fetchone()
    conn.close()
    return row