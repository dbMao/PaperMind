"""
Chat API 请求/响应模型。
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChatAskRequest(BaseModel):
    """RAG 问答请求"""
    question: str = Field(..., min_length=1, description="用户问题")
    paper_id: int | None = Field(default=None, description="单篇模式：论文 ID")
    selected_text: str | None = Field(default=None, description="划词选中的文本")
    session_id: int | str | None = Field(default=None, description="继续已有会话的 session_id")
    mode: Literal["single", "global"] = Field(default="single", description="对话模式")
    reasoning_effort: Literal["low", "medium", "high"] = Field(
        default="medium", description="推理强度"
    )
    preset_id: Literal["summarize", "compare", "algorithm", "references"] | None = Field(
        default=None, description="预设功能 ID"
    )
    paper_ids: list[int] | None = Field(
        default=None, description="对比模式：选中的论文 ID 列表"
    )


class SessionResponse(BaseModel):
    """会话列表项"""
    id: int
    title: str | None = None
    paper_id: int | None = None
    mode: str = "single"
    message_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """消息历史项"""
    id: int
    role: str
    content: str
    sources: list = []
    created_at: datetime | None = None

    class Config:
        from_attributes = True
