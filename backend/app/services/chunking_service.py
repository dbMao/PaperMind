"""
文档切分服务 —— 基于论文节标题的语义切分策略。

参数：
  - chunk_max_tokens: 1500（超长节按段落二次切分）
  - chunk_min_tokens: 200（相邻短节合并）
  - overlap_tokens: 200（二次切分时的重叠量）
"""

import logging
from dataclasses import dataclass, field

import tiktoken

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """文档块"""
    text: str
    metadata: dict = field(default_factory=dict)
    token_count: int = 0


class ChunkingService:
    """基于节标题的语义切分器"""

    MAX_TOKENS = 1500
    MIN_TOKENS = 200
    OVERLAP_TOKENS = 200
    ENCODING = "cl100k_base"

    def __init__(self):
        try:
            self._tokenizer = tiktoken.get_encoding(self.ENCODING)
        except Exception:
            self._tokenizer = tiktoken.get_encoding("o200k_base")
            logger.warning(f"无法加载 {self.ENCODING}，回退到 o200k_base")

    def _count_tokens(self, text: str) -> int:
        """计算文本的 token 数"""
        try:
            return len(self._tokenizer.encode(text))
        except Exception:
            return len(text) // 4  # 粗略估计

    def chunk_sections(
        self,
        sections: list,
        paper_id: int,
        paper_title: str,
    ) -> list[Chunk]:
        """
        对论文的节列表进行切分。

        Args:
            sections: Section 对象列表（来自 parser）
            paper_id: 论文 ID
            paper_title: 论文标题

        Returns:
            Chunk 列表
        """
        candidates = []

        # Step 1: 节 → 候选 chunk
        for section in sections:
            text = f"{section.title}\n\n{section.content}"
            token_count = self._count_tokens(text)

            if token_count <= self.MAX_TOKENS:
                candidates.append(self._make_chunk(
                    text=text,
                    paper_id=paper_id,
                    paper_title=paper_title,
                    section=section,
                    token_count=token_count,
                ))
            else:
                # 超长节 → 按段落二次切分
                sub_chunks = self._split_long_section(
                    text, paper_id, paper_title, section
                )
                candidates.extend(sub_chunks)

        # Step 2: 合并短 chunk
        merged = self._merge_short_chunks(candidates)

        # Step 3: 分配 chunk_index
        for i, chunk in enumerate(merged):
            chunk.metadata["chunk_index"] = i

        logger.info(
            f"论文 [{paper_title}] 切分完成: {len(sections)} 节 → {len(merged)} chunks"
        )
        return merged

    def _make_chunk(
        self,
        text: str,
        paper_id: int,
        paper_title: str,
        section,
        token_count: int = 0,
    ) -> Chunk:
        return Chunk(
            text=text,
            metadata={
                "paper_id": paper_id,
                "title": paper_title,
                "section": section.title if hasattr(section, "title") else "",
                "heading_level": section.level if hasattr(section, "level") else 2,
                "page": section.page_start if hasattr(section, "page_start") else 0,
                "chunk_index": -1,
            },
            token_count=token_count or self._count_tokens(text),
        )

    def _split_long_section(
        self,
        text: str,
        paper_id: int,
        paper_title: str,
        section,
    ) -> list[Chunk]:
        """按段落边界切分超长节，相邻子 chunk 之间有 200 token overlap"""
        paragraphs = text.split("\n\n")
        chunks = []
        buffer = ""
        buffer_tokens = 0
        overlap_text = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_tokens = self._count_tokens(para)

            if buffer_tokens + para_tokens > self.MAX_TOKENS and buffer:
                # 产出当前 chunk
                chunks.append(self._make_chunk(
                    text=buffer,
                    paper_id=paper_id,
                    paper_title=paper_title,
                    section=section,
                    token_count=buffer_tokens,
                ))
                # 提取最后 ~200 tokens 作为 overlap
                overlap_words = buffer.split()
                overlap_start = max(0, len(overlap_words) - self.OVERLAP_TOKENS // 2)
                overlap_text = " ".join(overlap_words[overlap_start:])
                buffer = overlap_text + "\n\n" + para
                buffer_tokens = self._count_tokens(buffer)
            else:
                if buffer:
                    buffer += "\n\n"
                buffer += para
                buffer_tokens += para_tokens

        if buffer:
            chunks.append(self._make_chunk(
                text=buffer,
                paper_id=paper_id,
                paper_title=paper_title,
                section=section,
                token_count=buffer_tokens,
            ))

        return chunks

    def _merge_short_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """合并相邻的短 chunk（均 < MIN_TOKENS）"""
        if len(chunks) <= 1:
            return chunks

        merged = []
        buffer = []
        buffer_tokens = 0

        for chunk in chunks:
            if chunk.token_count < self.MIN_TOKENS:
                buffer.append(chunk)
                buffer_tokens += chunk.token_count
                if buffer_tokens >= self.MIN_TOKENS:
                    merged.append(self._merge_chunk_list(buffer))
                    buffer = []
                    buffer_tokens = 0
            else:
                if buffer:
                    merged.append(self._merge_chunk_list(buffer))
                    buffer = []
                    buffer_tokens = 0
                merged.append(chunk)

        if buffer:
            merged.append(self._merge_chunk_list(buffer))

        return merged

    def _merge_chunk_list(self, chunks: list[Chunk]) -> Chunk:
        """合并多个 chunk 为一个"""
        combined_text = "\n\n".join(c.text for c in chunks)
        # 使用第一个 chunk 的元数据
        meta = chunks[0].metadata.copy() if chunks else {}
        return Chunk(
            text=combined_text,
            metadata=meta,
            token_count=sum(c.token_count for c in chunks),
        )


chunking_service = ChunkingService()
