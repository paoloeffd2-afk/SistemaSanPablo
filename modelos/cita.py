"""Cita ambulatoria (RF-02)."""
from datetime import datetime, timedelta


class Cita:
    PROGRAMADA, CANCELADA = "Programada", "Cancelada"

    def __init__(self, paciente, medico, consultorio, inicio: datetime, duracion_min: int = 30):
        self.__paciente, self.__medico, self.__consultorio = paciente, medico, consultorio
        self.__inicio = inicio
        self.__duracion = timedelta(minutes=duracion_min)
        self.__estado = Cita.PROGRAMADA

    paciente = property(lambda s: s.__paciente)
    medico = property(lambda s: s.__medico)
    consultorio = property(lambda s: s.__consultorio)
    inicio = property(lambda s: s.__inicio)
    estado = property(lambda s: s.__estado)

    @property
    def fin(self) -> datetime:
        return self.__inicio + self.__duracion

    def se_cruza_con(self, inicio: datetime, fin: datetime) -> bool:
        return self.__estado == Cita.PROGRAMADA and self.__inicio < fin and inicio < self.fin

    def cancelar(self) -> None:
        self.__estado = Cita.CANCELADA

    def reprogramar(self, nuevo_inicio: datetime) -> None:
        self.__inicio = nuevo_inicio

    def __repr__(self) -> str:
        return (f"Cita({self.__paciente.documento_enmascarado}, {self.__medico.nombres}, "
                f"{self.__inicio:%d/%m/%Y %H:%M}, {self.__estado})")
