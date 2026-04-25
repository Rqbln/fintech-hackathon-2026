import pytest


@pytest.fixture(autouse=True)
def clear_document_ai_client_cache():
    """Clear the lru_cache on _client() so mocks work correctly between tests."""
    from app.services import document_ai
    document_ai._client.cache_clear()
    yield
    document_ai._client.cache_clear()
