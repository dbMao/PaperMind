"""
Embedding 服务 —— 基于 sentence-transformers/all-MiniLM-L6-v2 的本地向量化。

首次使用需执行 scripts/deploy_embedding.py 下载模型（~90MB）。
模型下载到本地后，推理完全离线运行，数据不出本机。
"""

from pathlib import Path
from app.core.config import settings

MODEL_DIR = Path(settings.EMBEDDING_MODEL_DIR or "./models/all-MiniLM-L6-v2")
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class EmbeddingService:
    """本地 Embedding 服务 —— 懒加载单例"""

    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def is_deployed(self) -> bool:
        """检查模型是否已下载到本地"""
        if MODEL_DIR.exists() and any(MODEL_DIR.iterdir()):
            return True
        # 也检查 HuggingFace 缓存（用户可能通过其他方式下载过）
        try:
            from huggingface_hub import scan_cache_dir
            cache = scan_cache_dir()
            for repo in cache.repos:
                if MODEL_NAME in repo.repo_id:
                    return True
        except Exception:
            pass
        return False

    def deploy(self) -> dict:
        """下载模型到本地目录（如果已在 HF 缓存中则直接复制）。"""
        # 如果本地目录已有模型文件，直接返回
        if MODEL_DIR.exists() and any(MODEL_DIR.iterdir()):
            return {"status": "deployed", "message": "模型已部署"}

        try:
            from sentence_transformers import SentenceTransformer

            MODEL_DIR.mkdir(parents=True, exist_ok=True)

            model = SentenceTransformer(MODEL_NAME)
            model.save(str(MODEL_DIR))

            self._model = model

            return {"status": "deployed", "message": "Embedding 模型部署成功"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _load_model(self):
        """懒加载模型到内存"""
        if self._model is not None:
            return

        from sentence_transformers import SentenceTransformer

        if self.is_deployed and MODEL_DIR.exists() and any(MODEL_DIR.iterdir()):
            self._model = SentenceTransformer(str(MODEL_DIR))
        else:
            self._model = SentenceTransformer(MODEL_NAME)

    def encode(self, texts: list[str]) -> list[list[float]]:
        """将文本列表转为向量列表。"""
        self._load_model()
        embeddings = self._model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def encode_single(self, text: str) -> list[float]:
        """将单段文本转为向量。"""
        return self.encode([text])[0]


embedding_service = EmbeddingService()
