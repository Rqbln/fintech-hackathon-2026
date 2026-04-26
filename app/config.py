from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM provider: "cerebras" | "gemini"
    llm_provider: str = "gemini"

    # Cerebras inference (OpenAI-compatible)
    cerebras_api_key: str = ""
    cerebras_base_url: str = "https://api.cerebras.ai/v1"
    cerebras_model: str = "llama3.1-8b"

    # Gemini LLM (Google AI Studio — same key as embeddings)
    gemini_llm_model: str = "gemini-3-flash-preview"
    fast_mode: bool = False

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
    # Backward compatible single bucket
    gcs_bucket: str | None = None
    # Optional split buckets
    gcs_bucket_contrat: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCS_BUCKET_CONTRAT", "GCS_BUCKET_contrat", "gcs_bucket_contrat"),
    )
    gcs_bucket_dora: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCS_BUCKET_DORA", "GCS_BUCKET_dora", "gcs_bucket_dora"),
    )
    gcs_dora_object: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCS_DORA_OBJECT", "gcs_dora_object"),
    )

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str

    # LlamaParse (None → PyMuPDF fallback)
    llama_parse_api_key: str | None = None
    llama_parse_enabled: bool = False

    # App
    log_level: str = "INFO"
    traces_dir: str = "./traces"
    gap_concurrency: int = 4
    gap_batch_size: int = 2
    rag_cache_ttl_sec: int = 180
    finding_cache_ttl_sec: int = 300
    obligation_prefilter_enabled: bool = True

    @model_validator(mode="after")
    def _validate_gcs_buckets(self):
        # Require at least one contract bucket to keep startup failure explicit.
        if not (self.gcs_bucket or self.gcs_bucket_contrat):
            raise ValueError("Set GCS_BUCKET or GCS_BUCKET_CONTRAT in .env")
        return self

    @property
    def contract_bucket(self) -> str:
        return self.gcs_bucket_contrat or self.gcs_bucket or ""

    @property
    def dora_bucket(self) -> str:
        return self.gcs_bucket_dora or self.gcs_bucket_contrat or self.gcs_bucket or ""


settings = Settings()
