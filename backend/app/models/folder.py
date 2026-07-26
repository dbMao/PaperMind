"""
文件夹 API 请求/响应模型。
"""

from datetime import datetime

from pydantic import BaseModel, Field


class FolderCreate(BaseModel):
    """创建文件夹"""
    name: str = Field(..., min_length=1, max_length=256, description="文件夹名称")
    parent_id: int | None = Field(default=None, description="父文件夹 ID")


class FolderUpdate(BaseModel):
    """更新文件夹名称"""
    name: str = Field(..., min_length=1, max_length=256, description="新名称")


class FolderResponse(BaseModel):
    """文件夹响应"""
    id: int
    name: str
    parent_id: int | None = None
    is_default: bool = False
    paper_count: int = 0
    created_at: datetime | None = None

    class Config:
        from_attributes = True
