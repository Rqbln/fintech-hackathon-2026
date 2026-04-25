import logging
import os
import structlog


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=logging.getLevelName(level))
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level)),
        logger_factory=structlog.PrintLoggerFactory(),
    )


def get_trace_logger(session_id: str) -> structlog.BoundLogger:
    """Returns a logger that writes to ./traces/{session_id}.jsonl."""
    traces_dir = os.getenv("TRACES_DIR", "./traces")
    os.makedirs(traces_dir, exist_ok=True)
    trace_path = os.path.join(traces_dir, f"{session_id}.jsonl")
    file_handler = logging.FileHandler(trace_path, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    logger = logging.getLogger(f"trace.{session_id}")
    logger.addHandler(file_handler)
    logger.setLevel(logging.DEBUG)
    return structlog.wrap_logger(logger)
