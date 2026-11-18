"""Guarda los errores inesperados en error.log (junto a main.py) para poder revisarlos."""
import os
from datetime import datetime

RUTA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "error.log")


def guardar(detalle: str) -> str:
    """Agrega el error al archivo y devuelve la ruta (o '' si no se pudo escribir)."""
    try:
        with open(RUTA, "a", encoding="utf-8") as f:
            f.write(f"--- {datetime.now():%d/%m/%Y %H:%M:%S} ---\n{detalle}\n")
        return RUTA
    except OSError:
        return ""
