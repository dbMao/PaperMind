"""
论文 API 请求/响应模型。
"""

from datetime import datetime

from pydantic import BaseModel, Field


class PaperUpdate(BaseModel):
    """更新论文元数据"""
    title: str | None = Field(default=None, description="论文标题")
    authors: list[str] | None = Field(default=None, description="作者列表")
    year: int | None = Field(default=None, description="发表年份")
    abstract: str | None = Field(default=None, description="摘要")


class PaperMoveRequest(BaseModel):
    """移动论文到指定文件夹"""
    folder_id: int | None = Field(..., description="目标文件夹 ID，null 表示移出文件夹")


class PaperResponse(BaseModel):
    """论文响应"""
    id: int
    title: str
    authors: list[str] = []
    year: int | None = None
    abstract: str | None = None
    page_count: int | None = None
    folder_id: int | None = None
    status: str = "indexed"
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class SegmentResponse(BaseModel):
    """论文段落/节"""
    title: str  # 节标题
    level: int  # 标题层级
    content: str  # 节正文
    page_start: int
    page_end: int


class PaperSegmentsResponse(BaseModel):
    """论文段落列表响应"""
    title: str
    paragraphs: list[str]  # 前端 PaperViewer 期望的 paragraph 数组
    sections: list[SegmentResponse] = []
