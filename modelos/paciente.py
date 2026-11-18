"""Paciente con encapsulamiento (RF-01, RF-04, RD-02, RD-07)."""
import hmac
from datetime import date, datetime

from excepciones import DatoInvalidoError

TIPOS_DOCUMENTO = ("DNI", "CE", "PASAPORTE")
TIPOS_ASEGURAMIENTO = ("EPS", "SEGURO PRIVADO", "PARTICULAR")


def enmascarar_documento(numero: str) -> str:
    """Devuelve el documento como ******36 (solo los 2 últimos dígitos)."""
    return "*" * (len(numero) - 2) + numero[-2:]


def validar_documento(tipo: str, numero: str) -> str:
    numero = numero.strip()
    if tipo not in TIPOS_DOCUMENTO:
        raise DatoInvalidoError(f"Tipo de documento no válido: {tipo}.")
    if tipo == "DNI" and (len(numero) != 8 or not numero.isdigit()):
        raise DatoInvalidoError("El DNI debe tener exactamente 8 dígitos.")
    if tipo != "DNI" and not (9 <= len(numero) <= 12 and numero.isalnum()):
        raise DatoInvalidoError("El carné o pasaporte debe tener de 9 a 12 caracteres.")
    return numero


class ConsentimientoDatos:
    """Composición: no existe sin su Paciente (Ley N.° 29733)."""

    def __init__(self):
        self.fecha = datetime.now()


class Paciente:
    """El documento es privado y solo sale enmascarado."""

    def __init__(self, tipo_documento: str, numero_documento: str, nombres: str,
                 fecha_nacimiento: date, telefono: str = "",
                 aseguramiento: str = "PARTICULAR"):
        if not nombres.strip():
            raise DatoInvalidoError("Los nombres no pueden estar vacíos.")
        if fecha_nacimiento > date.today():
            raise DatoInvalidoError("La fecha de nacimiento no puede ser futura.")
        if aseguramiento not in TIPOS_ASEGURAMIENTO:
            raise DatoInvalidoError(f"Aseguramiento no válido: {aseguramiento}.")
        self.__tipo_documento = tipo_documento
        self.__numero_documento = validar_documento(tipo_documento, numero_documento)
        self.__nombres = nombres.strip().title()
        self.__fecha_nacimiento = fecha_nacimiento
        self.__telefono = telefono.strip()
        self.__aseguramiento = aseguramiento
        self.__consentimiento = None

    # --- getters (sin exponer el documento completo) ---
    @property
    def nombres(self) -> str:
        return self.__nombres

    @property
    def tipo_documento(self) -> str:
        return self.__tipo_documento

    @property
    def aseguramiento(self) -> str:
        return self.__aseguramiento

    @property
    def documento_enmascarado(self) -> str:
        return enmascarar_documento(self.__numero_documento)

    @property
    def edad(self) -> int:
        hoy = date.today()
        n = self.__fecha_nacimiento
        return hoy.year - n.year - ((hoy.month, hoy.day) < (n.month, n.day))

    # --- consentimiento (RF-04) ---
    def otorgar_consentimiento(self) -> None:
        self.__consentimiento = ConsentimientoDatos()

    @property
    def tiene_consentimiento(self) -> bool:
        return self.__consentimiento is not None

    # --- comparaciones dentro de la clase (RD-11) ---
    def es_mismo_paciente(self, otro: "Paciente") -> bool:
        return (self.__tipo_documento == otro.__tipo_documento
                and hmac.compare_digest(self.__numero_documento, otro.__numero_documento))

    def tiene_documento(self, tipo: str, numero: str) -> bool:
        return (self.__tipo_documento == tipo
                and hmac.compare_digest(self.__numero_documento, numero.strip()))

    def __repr__(self) -> str:
        return f"Paciente(doc={self.documento_enmascarado}, nombres={self.__nombres!r})"
