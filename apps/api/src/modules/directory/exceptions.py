"""
Module-owned exceptions for the directory module.

These exceptions extend ``AppError`` so they are automatically translated
to the unified error envelope by the global exception handler.

Error codes aligned with the API contract:
- DIRECTORY_QUERY_TOO_SHORT (400)
- DIRECTORY_INVALID_TYPE (400)
- DIRECTORY_ORG_NOT_FOUND (404)
- DIRECTORY_TREE_TOO_DEEP (400)
"""

from __future__ import annotations

from typing import Any

from ...utils.errors import AppError


class DirectoryQueryTooShortError(AppError):
    """Raised when the search query is too short (minimum 2 characters)."""

    def __init__(
        self, message: str = "搜索关键词过短，至少需要 2 个字符", details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(
            code="DIRECTORY_QUERY_TOO_SHORT",
            message=message,
            status_code=400,
            details=details,
        )


class DirectoryInvalidTypeError(AppError):
    """Raised when the search type is not one of all/users/organizations."""

    def __init__(
        self, message: str = "无效的搜索类型", details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(
            code="DIRECTORY_INVALID_TYPE",
            message=message,
            status_code=400,
            details=details,
        )


class DirectoryOrgNotFoundError(AppError):
    """Raised when the root organization for tree query is not found or not visible."""

    def __init__(
        self, message: str = "组织不存在或无权查看", details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(
            code="DIRECTORY_ORG_NOT_FOUND",
            message=message,
            status_code=404,
            details=details,
        )


class DirectoryTreeTooDeepError(AppError):
    """Raised when the requested tree depth exceeds the safety limit."""

    def __init__(
        self, message: str = "组织树深度超过安全上限", details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(
            code="DIRECTORY_TREE_TOO_DEEP",
            message=message,
            status_code=400,
            details=details,
        )
