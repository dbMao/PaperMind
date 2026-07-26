"""
Embedding 模型 API 路由
GET  /api/embedding/status  — 检查模型部署状态
POST /api/embedding/deploy  — 部署模型
"""

from fastapi import APIRouter
from pydantic import BaseModel
from app.services.embedding_service import embedding_service

router = APIRouter(prefix="/embedding", tags=["Embedding"])


class DeployResponse(BaseModel):
    status: str
    message: str


class StatusResponse(BaseModel):
    deployed: bool
    model_name: str
    model_size: str


@router.get("/status", response_model=StatusResponse)
async def get_status():
    """检查 Embedding 模型是否已部署"""
    return StatusResponse(
        deployed=embedding_service.is_deployed,
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_size="~90 MB",
    )


@router.post("/deploy", response_model=DeployResponse)
async def deploy_model():
    """部署（下载）Embedding 模型到本地"""
    result = embedding_service.deploy()
    return DeployResponse(**result)
