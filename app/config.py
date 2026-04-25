from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM — Cerebras inference (OpenAI-compatible)
    cerebras_api_key: str
    cerebras_base_url: str = "https://api.cerebras.ai/v1"
    cerebras_model: str = "llama3.1-8b"

    # Embeddings
    gemini_api_key: str
    gemini_embed_model: str = "models/gemini-embedding-2"
    gemini_embed_dim: int = 768  # Matryoshka reduction from 3072

    # Vertex AI Vector Search
    gcp_project: str
    gcp_region: str = "europe-west1"
    vertex_ai_vs_collection: str = "dora-analyst-docs"
    vertex_ai_vs_endpoint_id: str = ""

    # GCS
    gcs_bucket: str

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str

    # LlamaParse (None → PyMuPDF fallback)
    llama_parse_api_key: str | None = None

    # App
    log_level: str = "INFO"
    traces_dir: str = "./traces"


settings = Settings()
