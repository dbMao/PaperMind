from pathlib import Path
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

    # 数据存储目录
    DATA_DIR: str = "./data"

    # SQLite 数据库路径
    DATABASE_URL: str = ""

    # ChromaDB 持久化目录
    CHROMA_PERSIST_DIR: str = "./chroma_db"

    # Embedding 模型目录
    EMBEDDING_MODEL_DIR: str = "./models/all-MiniLM-L6-v2"

    @property
    def db_url(self) -> str:
        """计算数据库连接 URL"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        db_dir = Path(self.DATA_DIR)
        db_dir.mkdir(parents=True, exist_ok=True)
        return f"sqlite+aiosqlite:///{db_dir / 'papermind.db'}"

    @property
    def pdf_storage_dir(self) -> Path:
        """PDF 文件存储目录"""
        p = Path(self.DATA_DIR) / "pdfs"
        p.mkdir(parents=True, exist_ok=True)
        return p

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
