"""
对比检索服务 —— 两轮检索策略（全局 → 单篇补充 → 合并去重）。
"""

import logging

from langchain_core.documents import Document

from app.services.vector_service import vector_service

logger = logging.getLogger(__name__)


class CompareService:
    """两轮对比检索服务（单例）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def retrieve_for_compare(
        self,
        query: str,
        paper_ids: list[int],
        m: int = 10,
        n: int = 5,
    ) -> list[Document]:
        """
        两轮检索策略：
          1. 全局检索 top-m（不限论文）
          2. 对每篇命中论文单独检索 top-n
          3. 合并去重

        Args:
            query: 用户对比问题
            paper_ids: 用户选中的论文 ID 列表
            m: 第一轮全局检索数量
            n: 第二轮单篇检索数量

        Returns:
            去重后的 Document 列表
        """
        # Round 1: 全局检索
        round1 = vector_service.search(query=query, paper_id=None, k=m)
        logger.info(f"两轮检索 Round 1: 全局 top-{m} = {len(round1)} 条")

        # 记录第一轮命中的论文 ID
        hit_ids = set(doc.metadata.get("paper_id") for doc in round1)

        # 确保所有用户选中的论文都被覆盖
        targeted_ids = set(paper_ids) | hit_ids

        # Round 2: 对每篇论文单独补充检索
        round2 = []
        for pid in targeted_ids:
            results = vector_service.search(query=query, paper_id=pid, k=n)
            round2.extend(results)

        logger.info(f"两轮检索 Round 2: {len(targeted_ids)} 篇论文 × top-{n} = {len(round2)} 条")

        # 合并去重（按 chunk 文本 hash）
        all_results = round1 + round2
        seen = set()
        deduped = []
        for doc in all_results:
            doc_hash = hash(doc.page_content)
            if doc_hash not in seen:
                seen.add(doc_hash)
                deduped.append(doc)

        logger.info(f"两轮检索合并去重后: {len(deduped)} 条（原始 {len(all_results)} 条）")
        return deduped


compare_service = CompareService()
