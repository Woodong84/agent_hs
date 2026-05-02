from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Anthropic (선택)
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-5-20251001"

    # ── Azure OpenAI 호환 (선택 — 설정 시 Anthropic보다 우선 사용)
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""          # ex) https://aitalentlab.skax.co.kr:18081
    AZURE_OPENAI_DEPLOYMENT: str = "gpt-4.1" # LLM 모델명
    AZURE_OPENAI_API_VERSION: str = "2024-12-01-preview"

    # ── Azure 임베딩 (선택 — 설정 시 HuggingFace 대신 사용)
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = "text-embedding-3-small"

    # ── 외부 API (선택)
    UNIPASS_API_KEY: str = ""

    # ── 경로 설정
    CHROMA_DB_PATH: str = "./data/chroma_db"
    AUDIT_LOG_PATH: str = "./logs/audit_log.json"
    CHROMA_COLLECTION_NAME: str = "hs_code_docs"

    # ── RAG 설정
    SIMILARITY_THRESHOLD: float = 0.75
    TOP_K_CHUNKS: int = 5
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    # ── HuggingFace 임베딩 (Azure 미설정 시 Fallback)
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    @property
    def use_azure(self) -> bool:
        """Azure OpenAI 키와 엔드포인트가 모두 설정된 경우 True"""
        return bool(self.AZURE_OPENAI_API_KEY and self.AZURE_OPENAI_ENDPOINT)

    @property
    def has_llm(self) -> bool:
        """사용 가능한 LLM 키가 하나라도 있으면 True"""
        return self.use_azure or bool(self.ANTHROPIC_API_KEY)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
