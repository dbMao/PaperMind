"""
页面 API 路由 — 动态从源 PDF 渲染页面图片 + 缓存
GET /api/papers/{id}/pages           — 页面元数据列表
GET /api/papers/{id}/pages/{page_num} — 单页图片（实时渲染 + 磁盘缓存）
"""

import base64
import logging
import os

import fitz
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings as app_settings
from app.core.response import success, error
from app.db.database import get_db
from app.api.deps import get_paper_or_404

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/papers", tags=["Pages"])

RENDER_DPI = 150
CACHE_DIR = app_settings.pdf_storage_dir.parent / "page_cache"


def _get_cache_path(paper_id: int, page_num: int) -> str:
    return str(CACHE_DIR / f"{paper_id}_p{page_num}.png")


@router.get("/{paper_id}/pages")
async def get_paper_pages(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取论文页面元数据（每页宽高，不含图片）"""
    paper = await get_paper_or_404(paper_id, db)

    if not paper.file_path or not os.path.exists(paper.file_path):
        return success({"pages": [], "message": "PDF 文件不存在"})

    try:
        doc = fitz.open(paper.file_path)
        pages = []
        for pn in range(len(doc)):
            pix = doc[pn].get_pixmap(dpi=RENDER_DPI)
            pages.append({
                "page": pn,
                "width": pix.width,
                "height": pix.height,
                "block_count": 0,
            })
        doc.close()
        return success({"pages": pages})
    except Exception as e:
        logger.error(f"获取页面元数据失败: {e}")
        return error(50001, f"获取页面信息失败: {str(e)[:200]}")


@router.get("/{paper_id}/pages/{page_num}")
async def get_single_page(
    paper_id: int,
    page_num: int,
    db: AsyncSession = Depends(get_db),
):
    """获取单页图片 base64（首次渲染后磁盘缓存，后续直接读取）"""
    paper = await get_paper_or_404(paper_id, db)

    if not paper.file_path or not os.path.exists(paper.file_path):
        return error(40402, "PDF 文件不存在")

    # 检查缓存
    cache_path = _get_cache_path(paper_id, page_num)
    if os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")
        return success({"page": page_num, "image": f"data:image/png;base64,{img_b64}"})

    # 实时渲染
    try:
        doc = fitz.open(paper.file_path)
        if page_num >= len(doc):
            doc.close()
            return error(40404, f"页码 {page_num} 不存在")
        page = doc[page_num]
        pix = page.get_pixmap(dpi=RENDER_DPI)
        img_bytes = pix.tobytes("png")
        doc.close()

        # 写入磁盘缓存
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "wb") as f:
            f.write(img_bytes)

        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
        return success({
            "page": page_num,
            "width": pix.width,
            "height": pix.height,
            "image": f"data:image/png;base64,{img_b64}",
        })
    except Exception as e:
        logger.error(f"渲染页面 #{page_num} 失败: {e}")
        return error(50001, f"页面渲染失败: {str(e)[:200]}")
