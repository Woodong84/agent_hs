from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM
    ANTHROPIC_API_KEY: str = ""

    # 외부 API (선택)
    UNIPASS_API_KEY: str = ""

    # 경로 설정
    CHROMA_DB_PATH: str = "./data/chroma_db"
    AUDIT_LOG_PATH: str = "./logs/audit_log.json"
    CHROMA_COLLECTION_NAME: str = "hs_code_docs"

    # RAG 설정
    SIMILARITY_THRESHOLD: float = 0.75
    TOP_K_CHUNKS: int = 5
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    # LLM 모델명
    ANTHROPIC_MODEL: str = "claude-sonnet-4-5-20251001"

    # 임베딩 모델 (HuggingFace, 무료 로컬)
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
