"""Reporte semanal con programación funcional (RF-06, RD-08): funciones puras."""
from datetime import timedelta
from functools import reduce


def grupo_edad(edad: int) -> str:
    if edad <= 11:
        return "Niño (0-11)"
    if edad <= 17:
        return "Adolescente (12-17)"
    if edad <= 59:
        return "Adulto (18-59)"
    return "Adulto mayor (60+)"


def contar(acumulado: dict, clave: str) -> dict:
    return {**acumulado, clave: acumulado.get(clave, 0) + 1}


def atenciones_de_semana(atenciones, lunes) -> list:
    domingo = lunes + timedelta(days=6)
    return list(filter(lambda a: lunes <= a.fecha <= domingo, atenciones))


def resumen_por_especialidad(atenciones) -> dict:
    return reduce(contar, map(lambda a: a.especialidad, atenciones), {})


def resumen_por_grupo_edad(atenciones) -> dict:
    return reduce(contar, map(lambda a: grupo_edad(a.edad_paciente), atenciones), {})


def ingreso_total(atenciones) -> float:
    return reduce(lambda total, a: total + a.costo, atenciones, 0.0)
