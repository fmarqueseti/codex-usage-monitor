import logging
import os


def configure_logging() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def cache_ttl() -> float:
    return float(os.getenv("USAGE_CACHE_TTL", "60"))
