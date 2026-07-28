"""
对话服务 —— RAG 管线编排：检索 → 构建 Prompt → LLM 流式生成。
"""

import json
import logging
import uuid
from typing import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm import create_llm_from_config
from app.db.database import async_session as _new_session
from app.db.models import LLMSettings, ChatSession, ChatMessage
from app.services.vector_service import vector_service
from app.services.compare_service import compare_service
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)

# 预设 Prompt 模板（与前端 prompts.js 保持一致）
PRESET_PROMPTS = {
    "summarize": """你是一位专业的学术论文审稿人。请基于提供的论文内容，生成一份结构化的论文摘要。

要求：
1. 按以下结构输出：研究背景与目标 → 方法与实验设计 → 主要发现 → 结论与贡献 → 局限性
2. 每个部分用小标题标注，层次清晰
3. 使用学术语言，简洁准确
4. 总字数控制在 500-800 字
5. 如果论文内容不足以覆盖某一部分，请明确标注「论文未提及」
""",
    "compare": """你是一位学术研究对比分析专家。请基于提供的多篇论文内容，进行系统性的对比分析。

要求：
1. 按以下维度逐项对比：研究问题、方法论、数据集/实验设置、核心结果、创新点、局限性
2. 先用表格展示各维度对比，再用文字进行深度分析
3. 指出各论文之间的共识与分歧
4. 分析各方法的优劣及适用场景
5. 如果有明显的"空白地带"（所有论文都未覆盖的点），请指出
""",
    "algorithm": """你是一位算法与系统设计专家。请对论文中涉及的算法/方法进行深入的技术分析。

要求：
1. 梳理算法的输入、输出、核心步骤
2. 分析时间/空间复杂度
3. 识别算法中的关键设计决策与 trade-off
4. 与论文中提到的 baseline 方法进行对比
5. 讨论算法的可扩展性和潜在改进方向
6. 如果有伪代码或公式，用通俗语言解释其含义
""",
    "references": """你是一位学术文献管理专家。请基于论文内容和引文信息，整理结构化的参考文献分析。

要求：
1. 列出论文中引用的关键参考文献（区分奠基性工作、对比方法、数据来源等）
2. 对每篇关键引用说明其与本论文的关系（如：baseline、理论基础、改进对象等）
3. 如果需要，推荐 3-5 篇相关但未被引用的论文（基于你的知识库）
4. 分析该论文在引用网络中的位置（承前启后的关系）
5. 用 Markdown 表格和列表混合的方式组织
""",
}

DEFAULT_SYSTEM_PROMPT = """你是一个专业的论文阅读助手。请严格基于提供的论文内容回答用户的问题。

要求：
1. 仅在提供的论文内容范围内作答
2. 如果论文内容不足以回答问题，请明确说明
3. 回答时引用具体的章节和段落
4. 使用中文回答（除非用户要求用英文）

论文内容：
{context}"""


class ChatService:
    """RAG 对话服务（单例）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def ask_stream(
        self,
        question: str,
        paper_id: int | None,
        selected_text: str | None,
        session_id: str | None,
        mode: str,
        reasoning_effort: str,
        preset_id: str | None,
        paper_ids: list[int] | None,
        db: AsyncSession,
    ) -> AsyncGenerator[str, None]:
        """
        RAG 问答流式生成。

        Yields:
            SSE 事件 JSON 字符串：
            {"type": "chunk", "content": "..."}
            {"type": "sources", "sources": [...]}
            {"type": "done", "session_id": "..."}
        """
        # Step 1: 获取 LLM 配置
        result = await db.execute(select(LLMSettings).where(LLMSettings.id == 1))
        llm_settings = result.scalar_one_or_none()
        if not llm_settings or not llm_settings.api_key:
            yield self._sse("error", "请先在设置页配置 LLM API")
            return

        # 检查 embedding 模型
        if not embedding_service.is_deployed:
            yield self._sse("error", "Embedding 模型未部署，请先在设置页部署（~90MB）")
            return

        # Step 2: 构建上下文
        context_str = ""
        sources = []

        if selected_text:
            context_str = f"[用户选中的文本]\n{selected_text}\n\n"

        # 对比模式
        if preset_id == "compare" and mode == "global" and paper_ids and len(paper_ids) >= 2:
            retrieved = compare_service.retrieve_for_compare(
                query=question,
                paper_ids=paper_ids,
                m=10,
                n=5,
            )
        else:
            # 标准 RAG 检索
            search_paper_id = paper_id if mode == "single" else None
            retrieved = vector_service.search(
                query=question,
                paper_id=search_paper_id,
                k=5,
            )

        for doc in retrieved:
            title = doc.metadata.get("title", "")
            section = doc.metadata.get("section", "")
            page = doc.metadata.get("page", 0)
            chunk_text = doc.page_content[:500]
            context_str += f"[{title} - {section}]\n{doc.page_content}\n\n"
            sources.append({
                "paper_id": doc.metadata.get("paper_id", 0),
                "title": title,
                "section": section,
                "page": page,
                "chunk_text": chunk_text,
            })

        # 也检索历史对话消息（失败不阻塞主流程）
        try:
            msg_paper_id = paper_id if mode == "single" else None
            msg_docs = vector_service.search_messages(question, paper_id=msg_paper_id, k=3)
            if msg_docs:
                context_str += "\n[历史相关对话]\n"
                for doc in msg_docs:
                    role = doc.metadata.get("role", "")
                    context_str += f"[{role}]: {doc.page_content[:500]}\n"
        except Exception as e:
            logger.warning(f"历史对话检索失败（跳过）: {e}")

        if not context_str and not selected_text:
            context_str = "（未找到相关论文内容，请基于你的知识回答）"

        # Step 3: 构建 Prompt
        if preset_id and preset_id in PRESET_PROMPTS:
            system_prompt = PRESET_PROMPTS[preset_id] + "\n\n论文内容：\n{context}"
        else:
            system_prompt = DEFAULT_SYSTEM_PROMPT

        system_prompt = system_prompt.replace("{context}", context_str)

        # Step 4: 创建 LLM
        try:
            llm = create_llm_from_config(
                base_url=llm_settings.base_url,
                api_key=llm_settings.api_key,
                model=llm_settings.model,
                temperature=llm_settings.temperature,
                max_tokens=llm_settings.max_tokens,
                streaming=True,
            )
        except Exception as e:
            yield self._sse("error", f"创建 LLM 实例失败: {str(e)[:200]}")
            return

        # Step 5: 会话管理
        session = None
        if session_id:
            try:
                session = await db.get(ChatSession, int(session_id))
            except (ValueError, TypeError):
                pass

        if not session:
            session = ChatSession(
                title=question[:50],
                paper_id=paper_id,
                mode=mode,
            )
            db.add(session)
            await db.flush()
            await db.refresh(session)

        # 用独立 session 保存消息（避免 SSE 异常被 get_db 回滚）
        async def _save_msg(role: str, content: str, srcs: list = None) -> int:
            s = _new_session()
            async with s:
                msg = ChatMessage(session_id=session.id, role=role, content=content, sources=srcs or [])
                s.add(msg)
                await s.commit()
                await s.refresh(msg)
                return msg.id

        user_msg_id = await _save_msg("user", question)
        vector_service.add_message(user_msg_id, question, paper_id, session.id, "user")

        # Step 6: 流式生成
        full_response = ""
        try:
            from langchain_core.messages import SystemMessage, HumanMessage

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=question),
            ]

            for chunk in llm.stream(messages):
                content = chunk.content if hasattr(chunk, "content") else str(chunk)
                if content:
                    full_response += content
                    yield self._sse("chunk", content)
        except Exception as e:
            logger.exception("LLM 流式调用失败")
            yield self._sse("error", f"调用 LLM 失败: {str(e)[:300]}")
            await _save_msg("assistant", f"[错误] {str(e)[:500]}")
            return

        # 保存 assistant 消息
        assistant_msg_id = await _save_msg("assistant", full_response, sources)
        vector_service.add_message(assistant_msg_id, full_response, paper_id, session.id, "assistant")

        # Step 7: 发送 sources + done
        yield self._sse("sources", sources=sources)
        yield self._sse("done", session_id=str(session.id))

    def _sse(self, event_type: str, content: str = "", sources: list = None, session_id: str = "") -> str:
        """构建 SSE 事件 JSON"""
        data = {"type": event_type}
        if event_type == "chunk":
            data["content"] = content
        elif event_type == "sources":
            data["sources"] = sources or []
        elif event_type == "done":
            data["session_id"] = session_id
        elif event_type == "error":
            data["message"] = content
        return json.dumps(data, ensure_ascii=False)


chat_service = ChatService()
