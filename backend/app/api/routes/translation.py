"""
翻译 API 路由
POST /api/translation/status   — 检查模型部署状态
POST /api/translation/deploy   — 部署模型
POST /api/translation/translate— 翻译文本
"""

from fastapi import APIRouter
from pydantic import BaseModel
from app.services.translation_service import translation_service

router = APIRouter(prefix="/translation", tags=["Translation"])


class TranslateRequest(BaseModel):
    paragraphs: list[str]


class DeployResponse(BaseModel):
    status: str
    message: str


class StatusResponse(BaseModel):
    deployed: bool
    model_name: str


class TranslateResponse(BaseModel):
    translations: list[str]


@router.get("/status", response_model=StatusResponse)
async def get_status():
    """检查翻译模型是否已部署"""
    return StatusResponse(
        deployed=translation_service.is_deployed,
        model_name="Helsinki-NLP/opus-mt-en-zh",
    )


@router.post("/deploy", response_model=DeployResponse)
async def deploy_model():
    """部署（下载）翻译模型到本地"""
    result = translation_service.deploy()
    return DeployResponse(**result)


@router.post("/translate", response_model=TranslateResponse)
async def translate_text(req: TranslateRequest):
    """翻译段落列表（EN → ZH）"""
    if not translation_service.is_deployed:
        return TranslateResponse(
            translations=["错误：翻译模型未部署，请先调用 POST /api/translation/deploy"]
        )

    translations = translation_service.translate_batch(req.paragraphs)
    return TranslateResponse(translations=translations)
