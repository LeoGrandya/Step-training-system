"""TEXT-backed JSON serialization for MySQL 5.5-compatible columns."""

from __future__ import annotations

import json
from typing import Any

try:
    from sqlalchemy.types import Text, TypeDecorator
except ModuleNotFoundError:  # pragma: no cover - lets pure helper tests run without SQLAlchemy installed.
    Text = None
    TypeDecorator = None


def encode_json_text(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def decode_json_text(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    return json.loads(value)


if TypeDecorator is None:

    class JsonText:  # type: ignore[no-redef]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise RuntimeError("SQLAlchemy is required to use JsonText as a column type")

else:

    class JsonText(TypeDecorator):
        """Store JSON-compatible Python values as TEXT."""

        impl = Text
        cache_ok = True

        def process_bind_param(self, value: Any, dialect: Any) -> str | None:
            return encode_json_text(value)

        def process_result_value(self, value: Any, dialect: Any) -> Any:
            return decode_json_text(value)
