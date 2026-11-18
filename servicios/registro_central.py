"""RegistroCentral: patrón Singleton, único acceso a los datos en memoria (RD-05, RD-10)."""
from datetime import datetime

from excepciones import (AccesoDenegadoError, CitaCruzadaError, ConsentimientoRequeridoError,
                         NoEncontradoError, PacienteDuplicadoError)
from modelos.cita import Cita
from servicios.cifrador import Cifrador


class RegistroAcceso:
    """Composición: el registro de accesos pertenece al RegistroCentral (RD-02)."""

    def __init__(self, perfil: str, accion: str, documento_enmascarado: str):
        self.fecha = datetime.now()
        self.perfil, self.accion, self.documento = perfil, accion, documento_enmascarado

    def __repr__(self) -> str:
        return f"{self.fecha:%d/%m/%Y %H:%M:%S} | {self.perfil} | {self.accion} | {self.documento}"


class RegistroCentral:
    __instancia = None

    def __new__(cls):
        if cls.__instancia is None:
            obj = super().__new__(cls)
            obj.reiniciar()
            cls.__instancia = obj
        return cls.__instancia

    def reiniciar(self) -> None:
        """Vacía los datos (útil para pruebas y demostración)."""
        self.__pacientes, self.__citas, self.__atenciones = [], [], []
        self.__medicos, self.__consultorios, self.__accesos = [], [], []
        self.__cifrador = Cifrador()

    @property
    def cifrador(self) -> Cifrador:
        return self.__cifrador

    # ---------- catálogo (RF-05) ----------
    def agregar_medico(self, medico) -> None:
        self.__medicos.append(medico)

    def agregar_consultorio(self, consultorio) -> None:
        self.__consultorios.append(consultorio)

    def medicos(self) -> list:
        return list(self.__medicos)

    def consultorios(self) -> list:
        return list(self.__consultorios)

    # ---------- pacientes (RF-01, RF-04) ----------
    def registrar_paciente(self, paciente) -> None:
        if not paciente.tiene_consentimiento:
            raise ConsentimientoRequeridoError(
                "Debe registrar el consentimiento de datos personales antes de guardar.")
        if any(p.es_mismo_paciente(paciente) for p in self.__pacientes):
            raise PacienteDuplicadoError("Ya existe un paciente con ese documento.")
        self.__pacientes.append(paciente)

    def buscar_paciente(self, tipo: str, numero: str):
        for p in self.__pacientes:
            if p.tiene_documento(tipo, numero):
                return p
        raise NoEncontradoError("No se encontró un paciente con ese documento.")

    def cantidad_pacientes(self) -> int:
        return len(self.__pacientes)

    def pacientes(self) -> list:
        return list(self.__pacientes)

    # ---------- citas (RF-02) ----------
    def programar_cita(self, paciente, medico, consultorio, inicio, duracion_min=30) -> Cita:
        cita = Cita(paciente, medico, consultorio, inicio, duracion_min)
        self.__validar_horario(cita.inicio, cita.fin, medico, consultorio, ignorar=None)
        self.__citas.append(cita)
        return cita

    def reprogramar_cita(self, cita, nuevo_inicio) -> None:
        duracion = cita.fin - cita.inicio
        self.__validar_horario(nuevo_inicio, nuevo_inicio + duracion,
                               cita.medico, cita.consultorio, ignorar=cita)
        cita.reprogramar(nuevo_inicio)

    def cancelar_cita(self, cita) -> None:
        cita.cancelar()

    def __validar_horario(self, inicio, fin, medico, consultorio, ignorar) -> None:
        for c in self.__citas:
            if c is ignorar or not c.se_cruza_con(inicio, fin):
                continue
            if c.medico is medico or c.consultorio is consultorio:
                raise CitaCruzadaError("El médico o el consultorio ya tiene una cita en ese horario.")

    def citas(self) -> list:
        return list(self.__citas)

    def citas_de(self, paciente) -> list:
        return [c for c in self.__citas if c.paciente is paciente]

    # ---------- atenciones y diagnóstico (RF-03, RF-07) ----------
    def registrar_atencion(self, atencion) -> None:
        self.__atenciones.append(atencion)

    def atenciones(self) -> list:
        return list(self.__atenciones)

    def leer_diagnostico(self, atencion, personal) -> str:
        paciente = atencion.paciente
        if not personal.puede_ver_diagnostico:
            self.__accesos.append(RegistroAcceso(personal.perfil, "DENEGADO diagnóstico",
                                                 paciente.documento_enmascarado))
            raise AccesoDenegadoError("Su perfil no puede ver diagnósticos.")
        self.__accesos.append(RegistroAcceso(personal.perfil, "LEYÓ diagnóstico",
                                             paciente.documento_enmascarado))
        return self.__cifrador.descifrar(atencion.diagnostico_cifrado())

    def historial(self, tipo: str, numero: str, personal) -> list:
        """Citas y atenciones del paciente, sin documento completo ni diagnóstico (RF-07)."""
        return self.historial_de(self.buscar_paciente(tipo, numero), personal)

    def historial_de(self, paciente, personal) -> list:
        self.__accesos.append(RegistroAcceso(personal.perfil, "CONSULTÓ historial",
                                             paciente.documento_enmascarado))
        lineas = [f"Cita {c.inicio:%d/%m/%Y %H:%M} - {c.medico.nombres} - {c.estado}"
                  for c in self.citas_de(paciente)]
        lineas += [f"{a.tipo} {a.fecha:%d/%m/%Y} - {a.especialidad} - S/ {a.costo:.2f}"
                   for a in self.__atenciones if a.paciente is paciente]
        return lineas

    def accesos(self) -> list:
        return list(self.__accesos)
