"""
SQLAlchemy ORM 模型定义。

表：
  - LLMSettings: LLM API 配置（单行表）
  - Folder: 文件夹
  - Paper: 论文元数据
  - ChatSession: 对话会话
  - ChatMessage: 对话消息
"""

import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, Float, Boolean, JSON, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class LLMSettings(Base):
    """LLM API 配置（全局单行，id 固定为 1）"""

    __tablename__ = "llm_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    base_url: Mapped[str] = mapped_column(String(512), default="")
    api_key: Mapped[str] = mapped_column(String(512), default="")
    model: Mapped[str] = mapped_column(String(128), default="")
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    max_tokens: Mapped[int] = mapped_column(Integer, default=4096)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Folder(Base):
    """文件夹"""

    __tablename__ = "folders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("folders.id"), nullable=True
    )
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    papers = relationship("Paper", back_populates="folder", lazy="dynamic")


class Paper(Base):
    """论文元数据"""

    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(1024), nullable=False, default="未命名论文")
    authors: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    folder_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("folders.id"), nullable=True
    )
    # 翻译后的 PDF 路径
    translated_pdf_path: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    # 状态: processing → indexed → error
    status: Mapped[str] = mapped_column(String(32), default="indexed")
    # 存储解析后的节数据: [{title, level, content, page_start, page_end}, ...]
    sections_json: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    # 存储每页渲染数据: [{page, width, height, image_base64, blocks: [{text, bbox, font_size}]}]
    pages_json: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    folder = relationship("Folder", back_populates="papers")


class ChatSession(Base):
    """对话会话"""

    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    paper_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # 对话模式: single / global
    mode: Mapped[str] = mapped_column(String(16), default="single")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    messages = relationship(
        "ChatMessage", back_populates="session", lazy="dynamic",
        cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    """对话消息"""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chat_sessions.id"), nullable=False
    )
    # 角色: user / assistant / system
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="")
    # 引用来源: [{paper_id, title, page, chunk_text}, ...]
    sources: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    session = relationship("ChatSession", back_populates="messages")
