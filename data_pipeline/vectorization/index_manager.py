"""Vertex AI Vector Search index creation and management."""


async def create_index(display_name: str, dimensions: int = 768) -> str:
    """Create a new Vector Search index. Returns the index resource name."""
    # TODO: Create index via Vertex AI SDK
    pass


async def deploy_index(index_name: str, endpoint_name: str) -> str:
    """Deploy an index to an endpoint for online queries."""
    # TODO: Deploy via Vertex AI SDK
    pass
