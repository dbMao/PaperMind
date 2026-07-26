"""
向量存储服务 —— ChromaDB + LangChain Embeddings 封装。
"""

import logging

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

from app.core.config import settings as app_settings
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)


class VectorService:
    """向量存储服务 —— 懒加载单例"""

    _instance = None
    _store: Chroma | None = None
    _embeddings: HuggingFaceEmbeddings | None = None
    _collection_name = "papers"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _ensure_init(self):
        """初始化 ChromaDB 和 embeddings"""
        if self._store is not None:
            return

        logger.info("初始化 VectorService...")

        model_name = "sentence-transformers/all-MiniLM-L6-v2"
        model_path = str(app_settings.EMBEDDING_MODEL_DIR)

        # 优先使用本地部署目录，其次 HF 缓存，最后在线下载
        from pathlib import Path
        local_dir = Path(model_path)
        if local_dir.exists() and any(local_dir.iterdir()):
            self._embeddings = HuggingFaceEmbeddings(
                model_name=model_path,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
            logger.info(f"使用本地 embedding 模型: {model_path}")
        elif embedding_service.is_deployed:
            # 模型在 HF 缓存中，使用模型名自动从缓存加载
            self._embeddings = HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
            logger.info(f"使用 HF 缓存 embedding 模型: {model_name}")
        else:
            self._embeddings = HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
            logger.info("首次下载 embedding 模型 (~90MB)，请耐心等待...")

        persist_dir = str(app_settings.CHROMA_PERSIST_DIR)
        self._store = Chroma(
            embedding_function=self._embeddings,
            persist_directory=persist_dir,
            collection_name=self._collection_name,
        )

    def add_chunks(
        self,
        chunks: list,
        paper_id: int,
        paper_title: str,
    ):
        """
        将 chunk 列表添加到向量索引。

        Args:
            chunks: Chunk 对象列表（来自 chunking_service）
            paper_id: 论文 ID
            paper_title: 论文标题
        """
        self._ensure_init()

        documents = []
        ids = []
        for i, chunk in enumerate(chunks):
            chunk_id = f"{paper_id}_{i}"
            doc = Document(
                page_content=chunk.text,
                metadata=chunk.metadata,
                id=chunk_id,
            )
            documents.append(doc)
            ids.append(chunk_id)

        if documents:
            self._store.add_documents(documents, ids=ids)
            logger.info(f"论文 [{paper_title}] 添加了 {len(documents)} 个向量")

    def delete_paper(self, paper_id: int):
        """删除指定论文的向量索引"""
        self._ensure_init()
        try:
            collection = self._store._collection
            collection.delete(where={"paper_id": paper_id})
            logger.info(f"已删除论文 #{paper_id} 的向量索引")
        except Exception as e:
            logger.warning(f"删除向量索引失败 (可能不存在): {e}")

    def search(
        self,
        query: str,
        paper_id: int | None = None,
        k: int = 5,
    ) -> list[Document]:
        """
        向量检索。

        Args:
            query: 查询文本
            paper_id: 限定论文 ID（None = 全局检索）
            k: 返回数量

        Returns:
            LangChain Document 列表
        """
        self._ensure_init()

        filter_dict = None
        if paper_id is not None:
            filter_dict = {"paper_id": paper_id}

        try:
            results = self._store.similarity_search(
                query,
                k=k,
                filter=filter_dict,
            )
            return results
        except Exception as e:
            logger.warning(f"向量检索失败 (可能 collection 为空): {e}")
            return []


vector_service = VectorService()
