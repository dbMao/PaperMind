"""
LLM 设置 API 路由
GET  /api/settings/llm      — 获取当前配置
PUT  /api/settings/llm      — 保存配置
POST /api/settings/llm/test — 测试连接
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success, error
from app.core.llm import create_llm_from_config
from app.db.database import get_db
from app.db.models import LLMSettings
from app.models.settings import (
    LLMConfigRequest,
    LLMConfigResponse,
    TestConnectionRequest,
    TestConnectionResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/llm")
async def get_llm_config(db: AsyncSession = Depends(get_db)):
    """获取当前 LLM 配置（API Key 脱敏）"""
    result = await db.execute(select(LLMSettings).where(LLMSettings.id == 1))
    row = result.scalar_one_or_none()
    if not row:
        return success(None, message="尚未配置")
    return success(LLMConfigResponse.from_db(row).model_dump())


@router.put("/llm")
async def save_llm_config(req: LLMConfigRequest, db: AsyncSession = Depends(get_db)):
    """保存 LLM 配置"""
    result = await db.execute(select(LLMSettings).where(LLMSettings.id == 1))
    row = result.scalar_one_or_none()

    if not row:
        row = LLMSettings(id=1)
        db.add(row)

    row.base_url = req.base_url
    row.api_key = req.api_key
    row.model = req.model
    row.temperature = req.temperature
    row.max_tokens = req.max_tokens

    await db.flush()
    await db.refresh(row)

    return success(
        LLMConfigResponse.from_db(row).model_dump(),
        message="配置已保存",
    )


@router.post("/llm/test")
async def test_llm_connection(
    req: TestConnectionRequest, db: AsyncSession = Depends(get_db)
):
    """测试 LLM 连接"""
    # 如果请求未填参数，从数据库读取
    base_url = req.base_url
    api_key = req.api_key
    model = req.model

    if not base_url or not api_key or not model:
        result = await db.execute(select(LLMSettings).where(LLMSettings.id == 1))
        row = result.scalar_one_or_none()
        if row:
            base_url = base_url or row.base_url
            api_key = api_key or row.api_key
            model = model or row.model

    if not base_url or not api_key or not model:
        return error(40005, "请先配置 LLM 连接参数")

    try:
        llm = create_llm_from_config(
            base_url=base_url,
            api_key=api_key,
            model=model,
            temperature=0.0,
            max_tokens=10,
            streaming=False,
        )
        response = llm.invoke("Reply with 'OK' only.")
        content = response.content.strip() if hasattr(response, "content") else str(response).strip()

        if content:
            return success({"ok": True}, message="连接成功，模型可用")
        else:
            return error(40005, "模型返回空响应，请检查 API 地址和密钥")
    except Exception as e:
        error_msg = str(e)
        logger.warning(f"LLM 连接测试失败: {error_msg}")
        # 提取最下游的错误原因
        if "Connection" in error_msg or "connect" in error_msg.lower():
            return error(40005, f"无法连接 API 服务: {error_msg[:200]}")
        if "Unauthorized" in error_msg or "401" in error_msg or "403" in error_msg:
            return error(40005, "API 密钥无效或无权访问")
        if "not found" in error_msg.lower() or "404" in error_msg:
            return error(40005, f"模型 '{model}' 不存在，请检查模型名称")
        return error(40005, f"连接失败: {error_msg[:300]}")
