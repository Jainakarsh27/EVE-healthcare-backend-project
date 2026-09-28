import contextvars
import logging
import sys

request_id_ctx_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


class RequestIDFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx_var.get() or "N/A"
        return True


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("eve_healthcare")
    logger.setLevel(log_level.upper())
    logger.addFilter(RequestIDFilter())

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level.upper())
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | req_id=%(request_id)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = setup_logging()
