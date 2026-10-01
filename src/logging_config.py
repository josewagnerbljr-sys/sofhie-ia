"""
Configuração central de logs. Todos os módulos usam isso em vez de print(),
para que o histórico fique registrado em arquivo (não só no terminal) e
sobreviva a reinícios — essencial para um sistema rodando 24h sem supervisão constante.
"""
import logging
import os
from logging.handlers import RotatingFileHandler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "data", "logs")
os.makedirs(LOG_DIR, exist_ok=True)


def get_logger(nome: str) -> logging.Logger:
    logger = logging.getLogger(nome)
    if logger.handlers:
        return logger  # evita duplicar handlers se chamado mais de uma vez

    logger.setLevel(logging.INFO)

    formato = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    arquivo = RotatingFileHandler(
        os.path.join(LOG_DIR, f"{nome}.log"), maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    arquivo.setFormatter(formato)
    logger.addHandler(arquivo)

    console = logging.StreamHandler()
    console.setFormatter(formato)
    logger.addHandler(console)

    return logger
