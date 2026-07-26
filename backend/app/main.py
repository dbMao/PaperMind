import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import select, text

from app.api.routes import embedding, settings as settings_routes, folders, papers, chat, pages, translate_pdf
from app.core.config import settings as app_settings
from app.core.response import error as error_response
from app.db.database import engine, async_session
from app.db.models import Base, Folder, LLMSettings

# 配置日志
logging.basicConfig(
    level=logging.DEBUG if app_settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("papermind")

app = FastAPI(
    title="PaperMind API",
    version="0.1.0",
    description="论文阅读与管理工具后端 API",
)

# CORS 中间件（开发环境允许所有来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(embedding.router, prefix="/api")
app.include_router(settings_routes.router, prefix="/api")
app.include_router(folders.router, prefix="/api")
app.include_router(papers.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(pages.router, prefix="/api")
app.include_router(translate_pdf.router, prefix="/api")


@app.on_event("startup")
async def startup():
    """应用启动：创建目录、初始化数据库表"""
    # 创建数据目录
    Path(app_settings.DATA_DIR).mkdir(parents=True, exist_ok=True)
    Path(app_settings.CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
    app_settings.pdf_storage_dir  # 自动创建 pdfs/ 目录

    # 创建数据库表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 数据库迁移
    async with engine.begin() as conn:
        for col_name, col_type in [("pages_json", "JSON"), ("translated_pdf_path", "VARCHAR(2048)")]:
            try:
                await conn.execute(
                    text(f"ALTER TABLE papers ADD COLUMN {col_name} {col_type}")
                )
                logger.info(f"数据库迁移: 添加 papers.{col_name} 列")
            except Exception:
                pass

    # 确保 LLM 配置表有一条默认记录
    async with async_session() as db:
        result = await db.execute(select(LLMSettings).where(LLMSettings.id == 1))
        if not result.scalar_one_or_none():
            db.add(LLMSettings(id=1))
            await db.commit()

    logger.info("PaperMind API 启动完成")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """参数校验失败 → 422"""
    errors = exc.errors()
    msg = errors[0].get("msg", "参数校验失败") if errors else "参数校验失败"
    return JSONResponse(
        status_code=422,
        content=error_response(422, f"参数校验失败: {msg}"),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常捕获 → 500"""
    logger.exception("未处理的异常")
    return JSONResponse(
        status_code=500,
        content=error_response(50001, "服务器内部错误"),
    )


@app.get("/")
async def root():
    return {"message": "PaperMind API is running", "version": "0.1.0"}
