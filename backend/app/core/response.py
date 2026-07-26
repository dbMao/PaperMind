"""
统一 API 响应格式。
所有路由都通过这两个函数返回标准 JSON 响应：

  成功: { "code": 0, "message": "success", "data": {...} }
  失败: { "code": 40001, "message": "错误描述", "data": null }
"""

from typing import Any


def success(data: Any = None, message: str = "success") -> dict:
    """成功响应"""
    return {"code": 0, "message": message, "data": data}


def error(code: int, message: str, data: Any = None) -> dict:
    """错误响应"""
    return {"code": code, "message": message, "data": data}


def paginated(
    items: list, total: int, page: int, page_size: int
) -> dict:
    """分页响应"""
    return success({
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })
