from datetime import datetime, timedelta
from typing import Any, Optional


class Cache:
    def __init__(self, ttl_seconds: int = 900):
        self._store: dict[str, tuple[Any, datetime]] = {}
        self._ttl = timedelta(seconds=ttl_seconds)

    def get(self, key: str) -> Optional[Any]:
        if key not in self._store:
            return None
        value, timestamp = self._store[key]
        if datetime.now() - timestamp > self._ttl:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (value, datetime.now())
