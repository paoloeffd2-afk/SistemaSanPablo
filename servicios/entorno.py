"""Carga de variables desde un archivo .env local (sin dependencias externas, RT-01).

El .env nunca se sube a Git (.gitignore). Solo se asignan las variables que no existan
ya en el entorno, de modo que una variable real del sistema siempre tiene prioridad.
"""
import os


def cargar_env(ruta: str) -> int:
    """Lee líneas CLAVE=valor de `ruta` y devuelve cuántas variables nuevas definió."""
    if not os.path.isfile(ruta):
        return 0
    definidas = 0
    with open(ruta, encoding="utf-8") as archivo:
        for linea in archivo:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, _, valor = linea.partition("=")
            clave, valor = clave.strip(), valor.strip().strip('"').strip("'")
            if clave and valor and clave not in os.environ:
                os.environ[clave] = valor
                definidas += 1
    return definidas
