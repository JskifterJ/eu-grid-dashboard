"""Shared pytest fixtures and hooks."""
import pytest
import app.routes as routes_module


@pytest.fixture(autouse=True)
def clear_route_caches():
    """Clear all module-level caches before each test to prevent state bleed."""
    routes_module.entso_cache._store.clear()
    routes_module.ai_cache._store.clear()
    routes_module.overview_cache._store.clear()
    routes_module.forecast_cache._store.clear()
    routes_module.ranking_cache._store.clear()
    yield
