from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "PaperMind"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # CORS 允许的来源
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # 翻译模型目录
    TRANSLATION_MODEL_DIR: str = "./models/opus-mt-en-zh"

    # Embedding 模型目录
    EMBEDDING_MODEL_DIR: str = "./models/all-MiniLM-L6-v2"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
