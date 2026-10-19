"""
Uygulama Günlükleme (Logger) Modülü
Teknik hataları logs/app.log dosyasına yazar.
"""
import logging
from core.config import LOG_PATH

def setup_logger(name: str = "nobet_app") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        try:
            LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                "%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except Exception:
            try:
                import tempfile
                from pathlib import Path
                fallback_log = Path(tempfile.gettempdir()) / "nobet_app.log"
                file_handler = logging.FileHandler(fallback_log, encoding="utf-8")
                file_handler.setLevel(logging.DEBUG)
                file_formatter = logging.Formatter(
                    "%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
                )
                file_handler.setFormatter(file_formatter)
                logger.addHandler(file_handler)
            except Exception:
                pass
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter("[%(levelname)s] %(message)s")
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
    return logger

logger = setup_logger()
