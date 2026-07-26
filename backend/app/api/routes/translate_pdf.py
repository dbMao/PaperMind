"""
PDF 翻译 API（基于 pdf2zh）
POST /api/papers/{id}/translate   — 生成翻译版 PDF
GET  /api/papers/{id}/translated  — 获取/下载翻译版 PDF
GET  /api/papers/{id}/translate/status — 检查翻译状态
"""

import asyncio
import logging
import os
import shutil

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings as app_settings
from app.core.response import success, error
from app.db.database import get_db
from app.db.models import LLMSettings, Paper
from app.api.deps import get_paper_or_404
from app.services.retain_pdf_client import retain_pdf_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/papers", tags=["Translation"])


@router.post("/{paper_id}/translate")
async def translate_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
):
    """调用 pdf2zh 生成翻译版 PDF"""
    paper = await get_paper_or_404(paper_id, db)

    if not paper.file_path or not os.path.exists(paper.file_path):
        return error(40402, "论文 PDF 文件不存在，请重新上传")

    result = await db.execute(select(LLMSettings).where(LLMSettings.id == 1))
    llm = result.scalar_one_or_none()
    if not llm or not llm.api_key:
        return error(40005, "请先在设置页配置大模型 API")

    logger.info(f"pdf2zh 翻译开始: paper #{paper_id}")

    loop = asyncio.get_running_loop()
    resp = await loop.run_in_executor(
        None,
        retain_pdf_client.translate_pdf,
        paper.file_path,
        llm.api_key,
        llm.base_url or "https://api.deepseek.com/v1",
        llm.model or "deepseek-chat",
        "zh",
    )

    if resp["success"] and resp["pdf_path"]:
        # 复制翻译结果到持久化目录
        dest_dir = app_settings.pdf_storage_dir / "translated"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / f"{paper_id}_translated.pdf"
        shutil.move(resp["pdf_path"], str(dest_path))

        paper.translated_pdf_path = str(dest_path)
        await db.flush()

        logger.info(f"pdf2zh 翻译完成: {dest_path}")
        return success(
            {"has_translation": True},
            message="翻译完成",
        )
    else:
        return error(50003, resp.get("message", "翻译失败"))


@router.get("/{paper_id}/translated")
async def get_translated_pdf(
    paper: Paper = Depends(get_paper_or_404),
):
    """获取翻译版 PDF"""
    if not paper.translated_pdf_path or not os.path.exists(paper.translated_pdf_path):
        return error(40404, "翻译版本不存在，请先生成翻译")

    return FileResponse(
        paper.translated_pdf_path,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"},
    )


@router.get("/{paper_id}/translate/status")
async def get_translate_status(
    paper: Paper = Depends(get_paper_or_404),
):
    """检查翻译状态"""
    has = bool(paper.translated_pdf_path and os.path.exists(paper.translated_pdf_path))
    return success({"has_translation": has})
