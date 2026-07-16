import json
import logging
import sys
from datetime import datetime
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_dict = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }
        if record.exc_info:
            log_dict["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            log_dict["stack_info"] = self.formatStack(record.stack_info)
        return json.dumps(log_dict, ensure_ascii=False)


def configure_logging(environment: str = "local") -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)

    if environment in ("prod", "dev"):
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(JsonFormatter())
    else:
        console_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def setup_logging(app_name: str = "edugraph") -> None:
    from app.core.config import get_settings

    settings = get_settings()
    configure_logging(settings.environment)
    logger = get_logger(app_name)
    logger.info(f"Logging configured for environment: {settings.environment}")


def log_business_metric(metric_name: str, value: float | int, **tags: Any) -> None:
    """记录业务指标到日志流，便于后续聚合分析。

    Args:
        metric_name: 指标名称，如 resource_generation_success_rate
        value: 指标值
        **tags: 附加标签，如 resource_type="document"
    """
    metric_logger = logging.getLogger("business_metric")
    payload: dict[str, Any] = {"business_metric": metric_name, "value": value}
    if tags:
        payload["tags"] = tags
    metric_logger.info(json.dumps(payload, ensure_ascii=False))
