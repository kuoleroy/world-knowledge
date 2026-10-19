"""通用响应结构：{success, data, meta, error}。"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

T = TypeVar("T")


class CamelModel(BaseModel):
    """输出统一使用 camelCase 键的基类。"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应体。"""

    success: bool
    data: T | None = None
    meta: dict[str, Any] = {}
    error: str | None = None


def success_response(data: Any = None, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    """构造成功响应。"""
    return {"success": True, "data": data, "meta": meta or {}, "error": None}


def error_response(message: str, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    """构造失败响应。"""
    return {"success": False, "data": None, "meta": meta or {}, "error": message}
