"""
对话 API 路由
POST /api/chat/ask              — RAG 问答（SSE 流式）
GET  /api/chat/sessions         — 对话历史列表
GET  /api/chat/sessions/{id}    — 某次对话的完整消息
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel

from app.core.response import success, error
from app.db.database import get_db
from app.db.models import ChatSession, ChatMessage
from app.models.chat import ChatAskRequest, SessionResponse, MessageResponse
from app.api.deps import get_session_or_404
from app.services.chat_service import chat_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/ask")
async def chat_ask(req: ChatAskRequest, db: AsyncSession = Depends(get_db)):
    """RAG 问答（SSE 流式）"""

    async def event_generator():
        async for event_str in chat_service.ask_stream(
            question=req.question,
            paper_id=req.paper_id,
            selected_text=req.selected_text,
            session_id=req.session_id,
            mode=req.mode,
            reasoning_effort=req.reasoning_effort,
            preset_id=req.preset_id,
            paper_ids=req.paper_ids,
            db=db,
        ):
            yield {"event": "message", "data": event_str}

    return EventSourceResponse(event_generator())


class CreateSessionRequest(BaseModel):
    title: str = "新对话"
    paper_id: int | None = None
    mode: str = "single"


@router.get("/sessions")
async def list_sessions(
    paper_id: int | None = Query(default=None),
    mode: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """对话历史列表（可按论文和模式筛选）"""
    query = select(ChatSession)
    if paper_id is not None:
        query = query.where(ChatSession.paper_id == paper_id)
    if mode:
        query = query.where(ChatSession.mode == mode)
    query = query.order_by(ChatSession.updated_at.desc())

    result = await db.execute(query)
    sessions = result.scalars().all()

    items = []
    for s in sessions:
        count_result = await db.execute(
            select(func.count(ChatMessage.id)).where(ChatMessage.session_id == s.id)
        )
        msg_count = count_result.scalar() or 0
        items.append(SessionResponse(
            id=s.id, title=s.title, paper_id=s.paper_id, mode=s.mode,
            message_count=msg_count, updated_at=s.updated_at,
        ).model_dump())

    return success(items)


@router.post("/sessions", status_code=201)
async def create_session(req: CreateSessionRequest, db: AsyncSession = Depends(get_db)):
    """创建新对话会话"""
    session = ChatSession(title=req.title, paper_id=req.paper_id, mode=req.mode)
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return success(SessionResponse(
        id=session.id, title=session.title, paper_id=session.paper_id, mode=session.mode,
        message_count=0, updated_at=session.created_at,
    ).model_dump(), message="会话已创建")


@router.delete("/sessions/{session_id}")
async def delete_session(
    session: ChatSession = Depends(get_session_or_404),
    db: AsyncSession = Depends(get_db),
):
    """删除对话会话及其消息"""
    await db.delete(session)
    await db.flush()
    return success(message="会话已删除")


@router.get("/sessions/{session_id}")
async def get_session_messages(
    session: ChatSession = Depends(get_session_or_404),
    db: AsyncSession = Depends(get_db),
):
    """获取某次对话的完整消息"""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
    )
    messages = result.scalars().all()
    items = [
        MessageResponse(
            id=m.id, role=m.role, content=m.content,
            sources=m.sources or [], created_at=m.created_at,
        ).model_dump()
        for m in messages
    ]
    return success(items)
