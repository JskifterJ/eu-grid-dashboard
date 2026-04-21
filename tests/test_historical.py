import os
import tempfile
import pytest

from app.historical import HistoricalStore, DailySummary


@pytest.fixture
def tmp_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield HistoricalStore(db_path=path)
    os.unlink(path)


def test_upsert_and_query(tmp_store):
    s = DailySummary(country="FR", date="2026-04-19", avg_co2=45.0, avg_price=72.0, renewable_pct=88.0)
    tmp_store.upsert(s)
    rows = tmp_store.query(country="FR", start="2026-04-19", end="2026-04-19")
    assert len(rows) == 1
    assert rows[0].avg_co2 == 45.0


def test_upsert_replaces_existing(tmp_store):
    tmp_store.upsert(DailySummary(country="FR", date="2026-04-19", avg_co2=45.0, avg_price=72.0, renewable_pct=88.0))
    tmp_store.upsert(DailySummary(country="FR", date="2026-04-19", avg_co2=50.0, avg_price=80.0, renewable_pct=85.0))
    rows = tmp_store.query(country="FR", start="2026-04-19", end="2026-04-19")
    assert len(rows) == 1
    assert rows[0].avg_co2 == 50.0


def test_query_respects_date_range(tmp_store):
    for d in ["2026-04-17", "2026-04-18", "2026-04-19"]:
        tmp_store.upsert(DailySummary(country="FR", date=d, avg_co2=45.0, avg_price=72.0, renewable_pct=88.0))
    rows = tmp_store.query(country="FR", start="2026-04-18", end="2026-04-19")
    assert len(rows) == 2
