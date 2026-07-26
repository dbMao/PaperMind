"""
LLM 工厂 —— 从数据库读取用户配置，动态创建 LangChain ChatOpenAI 实例。
"""

import logging

from langchain_openai import ChatOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


def create_llm_from_config(
    base_url: str,
    api_key: str,
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    streaming: bool = True,
) -> ChatOpenAI:
    """
    根据配置参数创建 LangChain ChatOpenAI 实例。

    Args:
        base_url: API 端点地址（兼容 OpenAI 格式）
        api_key: API 密钥
        model: 模型名称
        temperature: 0=精确, 2=随机
        max_tokens: 单次回复最大 token 数
        streaming: 是否启用流式输出

    Returns:
        配置好的 ChatOpenAI 实例
    """
    return ChatOpenAI(
        openai_api_key=api_key,
        openai_api_base=base_url.rstrip("/"),
        model_name=model,
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=streaming,
    )
