"""Shared fixtures for all tests.

Phase 0: minimal — just an async HTTP client against the app.
Phase 2+: add Neo4j test container fixture.
"""

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client():
    """Async test client — does NOT require real external services."""
    # Import here so missing .env vars don't crash collection when not testing main
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
