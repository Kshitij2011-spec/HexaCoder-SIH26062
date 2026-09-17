"""Safe Structured Logging for HexaCoders Polar Platform."""

import logging
import re
import sys
from typing import Optional
from backend.app.core.config import settings

# Sensitive keyword patterns to mask in logs
SENSITIVE_PATTERNS = [
    re.compile(r"(password|token|key|secret|authorization)=([^\s&]+)", re.IGNORECASE),
    re.compile(r"postgres(?:ql)?://([^:]+):([^@]+)@", re.IGNORECASE),
]


class SensitiveDataFilter(logging.Filter):
    """Sanitizes sensitive credentials, passwords, and tokens from log records."""
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self._sanitize(record.msg)
        if record.args:
            sanitized_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    sanitized_args.append(self._sanitize(arg))
                else:
                    sanitized_args.append(arg)
            record.args = tuple(sanitized_args)
        return True

    def _sanitize(self, text: str) -> str:
        for pattern in SENSITIVE_PATTERNS:
            text = pattern.sub(r"\1=******", text)
        return text


def setup_logging():
    """Initializes application logger with sensitive data filtering."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger = logging.getLogger("hexacoders")
    logger.setLevel(log_level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ"
        )
        handler.setFormatter(formatter)
        handler.addFilter(SensitiveDataFilter())
        logger.addHandler(handler)

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Returns a namespaced child logger configured with sensitive data filtering."""
    base_logger = setup_logging()
    if name:
        return logging.getLogger(f"hexacoders.{name}")
    return base_logger


logger = setup_logging()
