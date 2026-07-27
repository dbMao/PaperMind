"""
论文 API 路由
GET    /api/papers             — 论文列表（分页+筛选）
POST   /api/papers/upload      — 上传 PDF
GET    /api/papers/{id}        — 论文详情
PUT    /api/papers/{id}        — 更新元数据
DELETE /api/papers/{id}        — 删除论文
GET    /api/papers/{id}/segments — 获取论文段落
PUT    /api/papers/{id}/move   — 移动到文件夹
"""

import logging
import uuid

import os

from fastapi import APIRouter, Depends, Form, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings as app_settings
from app.core.response import success, error, paginated
from app.db.database import get_db
from app.db.models import Paper
from app.models.paper import (
    PaperUpdate,
    PaperMoveRequest,
    PaperResponse,
    PaperSegmentsResponse,
    SegmentResponse,
)
from app.api.deps import get_paper_or_404
from app.services.parser_service import parser_service
from app.services.chunking_service import chunking_service
from app.services.vector_service import vector_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/papers", tags=["Papers"])


@router.get("")
async def list_papers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=1000),
    folder_id: int | None = Query(default=None, description="文件夹 ID 筛选"),
    search: str | None = Query(default=None, description="标题搜索"),
    db: AsyncSession = Depends(get_db),
):
    """论文列表（分页）"""
    query = select(Paper)

    if folder_id is not None and folder_id != 0:
        query = query.where(Paper.folder_id == folder_id)

    if search:
        query = query.where(Paper.title.ilike(f"%{search}%"))

    # 总数
    count_q = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    # 分页
    query = query.order_by(Paper.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    papers = result.scalars().all()

    items = [
        PaperResponse(
            id=p.id,
            title=p.title,
            authors=p.authors or [],
            year=p.year,
            abstract=p.abstract,
            page_count=p.page_count,
            folder_id=p.folder_id,
            status=p.status,
            has_translation=bool(p.translated_pdf_path and os.path.exists(p.translated_pdf_path)),
            created_at=p.created_at,
        ).model_dump()
        for p in papers
    ]

    return paginated(items=items, total=total, page=page, page_size=page_size)


@router.post("/upload", status_code=201)
async def upload_paper(
    file: UploadFile = File(...),
    folder_id: int = Query(default=0, description="目标文件夹 ID，0=不归类"),
    enable_ai_enhance: bool = Form(default=False),
    db: AsyncSession = Depends(get_db),
):
    """上传 PDF 论文"""
    # 验证文件格式
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return error(40001, "文件格式不支持，请上传 PDF 文件")

    # 验证文件大小
    content = await file.read()
    max_size = 50 * 1024 * 1024  # 50MB
    if len(content) > max_size:
        return error(40002, f"文件过大，最大支持 {max_size // 1024 // 1024}MB")

    # 保存文件
    pdf_name = f"{uuid.uuid4().hex}.pdf"
    pdf_path = app_settings.pdf_storage_dir / pdf_name
    pdf_path.write_bytes(content)

    # folder_id 为 0 表示不归类
    actual_folder_id = folder_id if folder_id > 0 else None

    paper = Paper(
        title=file.filename.replace(".pdf", ""),
        folder_id=actual_folder_id,
        status="processing",
        file_path=str(pdf_path),
    )
    db.add(paper)
    await db.flush()
    await db.refresh(paper)

    try:
        # PDF 解析
        parsed = parser_service.parse(str(pdf_path), enable_ai_enhance=enable_ai_enhance)

        # 更新元数据
        paper.title = parsed.title or paper.title
        paper.authors = parsed.authors
        paper.year = parsed.year
        paper.abstract = parsed.abstract[:2000] if parsed.abstract else None
        paper.page_count = parsed.page_count

        # 存储节数据
        sections_json = [
            {
                "title": s.title,
                "level": s.level,
                "content": s.content,
                "page_start": s.page_start,
                "page_end": s.page_end,
            }
            for s in parsed.sections
        ]
        paper.sections_json = sections_json

        # 渲染页面图片 + 提取文字块坐标
        try:
            pages_data = parser_service.render_pages(str(pdf_path))
            paper.pages_json = pages_data
        except Exception as e:
            logger.warning(f"页面渲染失败（非致命）: {e}")
            paper.pages_json = []

        # Chunking + 向量化
        chunks = chunking_service.chunk_sections(
            sections=parsed.sections,
            paper_id=paper.id,
            paper_title=paper.title,
        )
        if chunks:
            vector_service.add_chunks(chunks, paper_id=paper.id, paper_title=paper.title)

        paper.status = "indexed"
        await db.flush()
        await db.refresh(paper)

        logger.info(f"论文上传完成: [{paper.id}] {paper.title}")

    except Exception as e:
        logger.exception(f"论文处理失败: {e}")
        paper.status = "error"
        await db.flush()
        await db.refresh(paper)
        return error(
            50002,
            f"论文处理失败: {str(e)[:200]}",
            {"paper_id": paper.id, "status": "error"},
        )

    return success(
        PaperResponse(
            id=paper.id,
            title=paper.title,
            authors=paper.authors or [],
            year=paper.year,
            abstract=paper.abstract,
            page_count=paper.page_count,
            folder_id=paper.folder_id,
            status=paper.status,
            created_at=paper.created_at,
        ).model_dump(),
        message="上传成功",
    )


@router.get("/{paper_id}")
async def get_paper(paper: Paper = Depends(get_paper_or_404)):
    """获取论文详情"""
    return success(
        PaperResponse(
            id=paper.id,
            title=paper.title,
            authors=paper.authors or [],
            year=paper.year,
            abstract=paper.abstract,
            page_count=paper.page_count,
            folder_id=paper.folder_id,
            status=paper.status,
            has_translation=bool(paper.translated_pdf_path and os.path.exists(paper.translated_pdf_path)),
            created_at=paper.created_at,
        ).model_dump()
    )


@router.put("/{paper_id}")
async def update_paper(
    req: PaperUpdate,
    paper: Paper = Depends(get_paper_or_404),
    db: AsyncSession = Depends(get_db),
):
    """更新论文元数据"""
    if req.title is not None:
        paper.title = req.title
    if req.authors is not None:
        paper.authors = req.authors
    if req.year is not None:
        paper.year = req.year
    if req.abstract is not None:
        paper.abstract = req.abstract

    await db.flush()
    await db.refresh(paper)

    return success(
        PaperResponse(
            id=paper.id,
            title=paper.title,
            authors=paper.authors or [],
            year=paper.year,
            abstract=paper.abstract,
            page_count=paper.page_count,
            folder_id=paper.folder_id,
            status=paper.status,
            created_at=paper.created_at,
        ).model_dump(),
        message="已更新",
    )


@router.delete("/{paper_id}")
async def delete_paper(
    paper: Paper = Depends(get_paper_or_404),
    db: AsyncSession = Depends(get_db),
):
    """删除论文（含 PDF 文件和向量索引）"""
    # 删除向量索引
    vector_service.delete_paper(paper.id)

    # 删除 PDF 文件
    if paper.file_path:
        try:
            import os
            if os.path.exists(paper.file_path):
                os.remove(paper.file_path)
        except Exception as e:
            logger.warning(f"删除 PDF 文件失败: {e}")

    await db.delete(paper)
    await db.flush()
    return success(message="论文已删除")


@router.get("/{paper_id}/segments")
async def get_paper_segments(paper: Paper = Depends(get_paper_or_404)):
    """获取论文段落（用于前端展示和翻译）"""
    sections_data = paper.sections_json or []

    # 前端 PaperViewer 期望的 paragraphs 数组（纯文本段落）
    paragraphs = []
    sections = []

    for s in sections_data:
        content = s.get("content", "")
        if content:
            # 将节内容按空行拆分为段落
            paras = [p.strip() for p in content.split("\n\n") if p.strip()]
            paragraphs.extend(paras)

        sections.append(
            SegmentResponse(
                title=s.get("title", ""),
                level=s.get("level", 2),
                content=content,
                page_start=s.get("page_start", 0),
                page_end=s.get("page_end", 0),
            )
        )

    # 如果没有段落数据，尝试从 abstract 生成
    if not paragraphs and paper.abstract:
        paragraphs = [p.strip() for p in paper.abstract.split(". ") if p.strip()]

    return success(
        PaperSegmentsResponse(
            title=paper.title,
            paragraphs=paragraphs,
            sections=sections,
        ).model_dump()
    )


@router.get("/{paper_id}/file")
async def get_paper_file(paper: Paper = Depends(get_paper_or_404)):
    """获取论文原始 PDF 文件（用于浏览器内嵌预览）"""
    if not paper.file_path or not os.path.exists(paper.file_path):
        return error(40402, "PDF 文件不存在")
    return FileResponse(
        paper.file_path,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"},
    )


@router.put("/{paper_id}/move")
async def move_paper(
    req: PaperMoveRequest,
    paper: Paper = Depends(get_paper_or_404),
    db: AsyncSession = Depends(get_db),
):
    """移动论文到指定文件夹"""
    paper.folder_id = req.folder_id if req.folder_id != 0 else None
    await db.flush()
    return success(message="已移动到目标文件夹")
