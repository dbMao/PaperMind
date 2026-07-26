"""
文件夹 API 路由
GET    /api/folders      — 文件夹列表
POST   /api/folders      — 创建文件夹
PUT    /api/folders/{id} — 重命名文件夹
DELETE /api/folders/{id} — 删除文件夹
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success, error
from app.db.database import get_db
from app.db.models import Folder, Paper
from app.models.folder import FolderCreate, FolderUpdate, FolderResponse
from app.api.deps import get_folder_or_404

router = APIRouter(prefix="/folders", tags=["Folders"])


@router.get("")
async def list_folders(db: AsyncSession = Depends(get_db)):
    """获取全部文件夹列表（含论文数量）"""
    result = await db.execute(select(Folder).order_by(Folder.created_at))
    folders = result.scalars().all()

    items = []
    for f in folders:
        # 统计论文数量
        count_result = await db.execute(
            select(func.count(Paper.id)).where(Paper.folder_id == f.id)
        )
        paper_count = count_result.scalar() or 0
        items.append(
            FolderResponse(
                id=f.id,
                name=f.name,
                parent_id=f.parent_id,
                is_default=f.is_default or False,
                paper_count=paper_count,
                created_at=f.created_at,
            )
        )

    return success([item.model_dump() for item in items])


@router.post("", status_code=201)
async def create_folder(req: FolderCreate, db: AsyncSession = Depends(get_db)):
    """创建文件夹"""
    folder = Folder(name=req.name, parent_id=req.parent_id)
    db.add(folder)
    await db.flush()
    await db.refresh(folder)

    return success(
        FolderResponse(
            id=folder.id,
            name=folder.name,
            parent_id=folder.parent_id,
            paper_count=0,
            created_at=folder.created_at,
        ).model_dump(),
        message="文件夹已创建",
    )


@router.put("/{folder_id}")
async def rename_folder(
    folder_id: int, req: FolderUpdate, db: AsyncSession = Depends(get_db)
):
    """重命名文件夹"""
    folder = await get_folder_or_404(folder_id, db)
    folder.name = req.name
    await db.flush()
    await db.refresh(folder)
    return success(message="文件夹已重命名")


@router.delete("/{folder_id}")
async def delete_folder(
    folder_id: int,
    force: bool = Query(default=False, description="强制删除（将论文移出文件夹）"),
    db: AsyncSession = Depends(get_db),
):
    """删除文件夹"""
    folder = await get_folder_or_404(folder_id, db)

    # 检查是否有论文
    count_result = await db.execute(
        select(func.count(Paper.id)).where(Paper.folder_id == folder_id)
    )
    paper_count = count_result.scalar() or 0

    if paper_count > 0:
        if force:
            # 将论文移出文件夹
            papers_result = await db.execute(
                select(Paper).where(Paper.folder_id == folder_id)
            )
            for p in papers_result.scalars():
                p.folder_id = None
            await db.flush()
        else:
            return error(
                40006,
                f"文件夹「{folder.name}」下还有 {paper_count} 篇论文，请先移出或使用 force=true 强制删除",
                {"paper_count": paper_count},
            )

    await db.delete(folder)
    await db.flush()
    return success(message="文件夹已删除")
