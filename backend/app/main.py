from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import example, translation, embedding
from app.core.config import settings

app = FastAPI(
    title="PaperMind API",
    version="0.1.0",
    description="论文阅读与管理工具后端 API",
)

# CORS 中间件（开发环境允许所有来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(example.router, prefix="/api")
app.include_router(translation.router, prefix="/api")
app.include_router(embedding.router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "PaperMind API is running", "version": "0.1.0"}
