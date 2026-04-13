import time
from app.cache import Cache


def test_cache_miss_returns_none():
    c = Cache(ttl_seconds=60)
    assert c.get("missing") is None


def test_cache_hit_returns_value():
    c = Cache(ttl_seconds=60)
    c.set("key", {"data": 42})
    assert c.get("key") == {"data": 42}


def test_cache_expired_returns_none():
    c = Cache(ttl_seconds=1)
    c.set("key", "value")
    time.sleep(1.1)
    assert c.get("key") is None


def test_cache_set_overwrites():
    c = Cache(ttl_seconds=60)
    c.set("key", "first")
    c.set("key", "second")
    assert c.get("key") == "second"
