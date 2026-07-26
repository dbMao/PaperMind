"""
LLM 设置 API 请求/响应模型。
"""

from pydantic import BaseModel, Field


class LLMConfigRequest(BaseModel):
    """保存 LLM 配置的请求体"""
    base_url: str = Field(default="", description="API 端点地址")
    api_key: str = Field(default="", description="API 密钥")
    model: str = Field(default="", description="模型名称")
    temperature: float = Field(default=0.7, ge=0, le=2, description="Temperature (0-2)")
    max_tokens: int = Field(default=4096, ge=256, le=131072, description="最大 token 数")


class LLMConfigResponse(BaseModel):
    """LLM 配置响应（API Key 脱敏）"""
    base_url: str
    api_key: str  # 已脱敏
    model: str
    temperature: float
    max_tokens: int

    @classmethod
    def from_db(cls, settings) -> "LLMConfigResponse":
        """从数据库记录创建响应，自动脱敏 api_key"""
        key = settings.api_key or ""
        masked = key
        if len(key) > 8:
            masked = key[:3] + "*" * (len(key) - 6) + key[-3:]
        return cls(
            base_url=settings.base_url,
            api_key=masked,
            model=settings.model,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
        )


class TestConnectionRequest(BaseModel):
    """测试 LLM 连接请求（可传入临时配置）"""
    base_url: str = ""
    api_key: str = ""
    model: str = ""


class TestConnectionResponse(BaseModel):
    """测试连接结果"""
    success: bool
    message: str
