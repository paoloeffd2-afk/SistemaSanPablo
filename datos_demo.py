"""Datos ficticios para la demostración (RD-03). Nunca se usan datos reales."""
from modelos.personal import Consultorio, Medico
from servicios.registro_central import RegistroCentral


def cargar_catalogo() -> RegistroCentral:
    registro = RegistroCentral()
    if registro.medicos():  # ya cargado: no duplicar el catálogo
        return registro
    for nombre, esp in [("Dr. Carlos Rojas", "Cardiología"), ("Dra. Lucía Paredes", "Pediatría"),
                        ("Dr. Mario Salas", "Medicina General")]:
        registro.agregar_medico(Medico(nombre, esp))
    for codigo in ("C-101", "C-102", "C-201"):
        registro.agregar_consultorio(Consultorio(codigo))
    return registro
