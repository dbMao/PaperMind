"""
FastAPI 共享依赖项。
"""

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Folder, LLMSettings, Paper, ChatSession
from app.core.response import error


async def get_folder_or_404(folder_id: int, db: AsyncSession = Depends(get_db)) -> Folder:
    """获取文件夹，不存在则返回 404"""
    folder = await db.get(Folder, folder_id)
    if not folder:
        raise HTTPException(
            status_code=404,
            detail=error(40401, "文件夹不存在"),
        )
    return folder


async def get_paper_or_404(paper_id: int, db: AsyncSession = Depends(get_db)) -> Paper:
    """获取论文，不存在则返回 404"""
    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(
            status_code=404,
            detail=error(40402, "论文不存在"),
        )
    return paper


async def get_session_or_404(session_id: int, db: AsyncSession = Depends(get_db)) -> ChatSession:
    """获取对话会话，不存在则返回 404"""
    session = await db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=error(40403, "会话不存在"),
        )
    return session


async def get_llm_settings(db: AsyncSession) -> LLMSettings | None:
    """获取 LLM 配置，不存在则返回 None"""
    result = await db.execute(select(LLMSettings).where(LLMSettings.id == 1))
    return result.scalar_one_or_none()
