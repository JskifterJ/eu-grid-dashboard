"""
Historicals live in on-disk SQLite (they're immutable; no need for Postgres).
See spec §8 and ADR 0001.
"""
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DailySummary:
    country: str
    date: str          # ISO YYYY-MM-DD
    avg_co2: float
    avg_price: float
    renewable_pct: float


_SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_summary (
    country TEXT NOT NULL,
    date TEXT NOT NULL,
    avg_co2 REAL NOT NULL,
    avg_price REAL NOT NULL,
    renewable_pct REAL NOT NULL,
    PRIMARY KEY (country, date)
);
"""


class HistoricalStore:
    def __init__(self, db_path: str):
        self._path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(_SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def upsert(self, s: DailySummary) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO daily_summary "
                "(country, date, avg_co2, avg_price, renewable_pct) VALUES (?, ?, ?, ?, ?)",
                (s.country, s.date, s.avg_co2, s.avg_price, s.renewable_pct),
            )

    def query(self, country: str, start: str, end: str) -> list[DailySummary]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT country, date, avg_co2, avg_price, renewable_pct "
                "FROM daily_summary WHERE country = ? AND date BETWEEN ? AND ? "
                "ORDER BY date",
                (country, start, end),
            ).fetchall()
        return [DailySummary(*row) for row in rows]
