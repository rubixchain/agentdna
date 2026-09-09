from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import structlog
from structlog.typing import FilteringBoundLogger

LOG_FORMAT_JSON = "json"
LOG_FORMAT_TEXT = "text"

supported_log_formats = [
    LOG_FORMAT_JSON,
    LOG_FORMAT_TEXT,
]


class _FileWriter:
    def __init__(self, path: Path, renderer: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._file = path.open("a", encoding="utf-8")
        self._renderer = renderer

    def __call__(
        self,
        logger: Any,
        method_name: str,
        event_dict: dict[str, Any],
    ) -> dict[str, Any]:
        rendered = self._renderer(
            logger,
            method_name,
            event_dict.copy(),
        )

        self._file.write(rendered)
        self._file.write("\n")
        self._file.flush()

        return event_dict


_file_writer: _FileWriter | None = None


def configure_logging(
    log_level: str = "INFO",
    log_format: str = LOG_FORMAT_JSON,
    log_file_path: str = "",
) -> None:
    global _file_writer

    if log_format not in supported_log_formats:
        raise ValueError(
            f"unsupported log_format: {log_format}. Supported formats: {supported_log_formats}"
        )

    numeric_level = getattr(logging, log_level.upper(), None)

    if not isinstance(numeric_level, int):
        raise ValueError(f"unsupported log_level: {log_level}")

    if log_format == LOG_FORMAT_JSON:
        console_renderer = structlog.processors.JSONRenderer()
        file_renderer = structlog.processors.JSONRenderer()
    else:
        console_renderer = structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty())
        file_renderer = structlog.dev.ConsoleRenderer(colors=False)

    base_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(
            fmt="iso",
            utc=True,
            key="timestamp",
        ),
    ]

    processors: list[Any] = [
        *base_processors,
    ]

    if log_file_path:
        _file_writer = _FileWriter(
            Path(log_file_path),
            file_renderer,
        )
        processors.append(_file_writer)

    processors.append(console_renderer)

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.PrintLoggerFactory(
            file=sys.stdout,
        ),
        cache_logger_on_first_use=True,
    )


def get_logger(
    name: str = "agentdna",
) -> FilteringBoundLogger:
    return structlog.get_logger(name)
