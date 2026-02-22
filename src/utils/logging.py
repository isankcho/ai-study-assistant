import logging


class HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return "/healthz" not in msg


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    for logger_name in ["uvicorn.access", "tornado.access", "streamlit.web.server"]:
        logger = logging.getLogger(logger_name)
        logger.addFilter(HealthCheckFilter())
