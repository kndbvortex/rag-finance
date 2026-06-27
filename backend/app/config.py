from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://rag:rag@localhost:5432/rag_db"

    searxng_url: str = "https://search.kndbvortex.cloud"

    embedding_model: str = "intfloat/multilingual-e5-large"
    reranker_model: str = "mixedbread-ai/mxbai-rerank-large-v1"

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = ""

    llm_provider: str = "cerebras"  # "groq" | "cerebras" | "local"

    groq_api_key: str = ""
    cerebras_api_key: str = ""
    llm_model: str = "zai-glm-4.7"
    llm_max_tokens: int = 2048

    local_llm_model: str = "meta-llama/Llama-3.2-3B-Instruct"


settings = Settings()
