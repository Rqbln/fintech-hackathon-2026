import pytest


@pytest.fixture(autouse=True)
def clear_document_ai_client_cache():
    """Clear the lru_cache on _client() so mocks work correctly between tests."""
    from app.services import document_ai
    document_ai._client.cache_clear()
    yield
    document_ai._client.cache_clear()


@pytest.fixture(autouse=True)
def reset_rag_initialized():
    """Reset the one-time init flag so vertexai mocks work correctly between tests."""
    import app.services.rag_engine as re
    re._initialized = False
    yield
    re._initialized = False
