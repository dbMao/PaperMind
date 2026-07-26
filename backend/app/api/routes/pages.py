"""
页面 API 路由
GET /api/papers/{id}/pages           — 获取论文页面数据（元数据，无图片）
GET /api/papers/{id}/pages/{page_num} — 获取单页数据（含图片 base64）
"""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success, error
from app.db.database import get_db
from app.api.deps import get_paper_or_404

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/papers", tags=["Pages"])


@router.get("/{paper_id}/pages")
async def get_paper_pages(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取论文全部页面元数据（不含 base64 图片，前端按需请求单页）"""
    paper = await get_paper_or_404(paper_id, db)
    pages = paper.pages_json or []

    if not pages:
        return success({"pages": [], "message": "页面数据尚未生成，请重新上传论文"})

    lite_pages = []
    for p in pages:
        lite_pages.append({
            "page": p["page"],
            "width": p["width"],
            "height": p["height"],
            "block_count": len(p.get("blocks", [])),
        })
    return success({"pages": lite_pages})


@router.get("/{paper_id}/pages/{page_num}")
async def get_single_page(
    paper_id: int,
    page_num: int,
    db: AsyncSession = Depends(get_db),
):
    """获取单页完整数据（含 base64 图片）"""
    paper = await get_paper_or_404(paper_id, db)
    pages = paper.pages_json or []

    if not pages or page_num >= len(pages):
        return error(40404, f"页码 {page_num} 不存在")

    return success(pages[page_num])
