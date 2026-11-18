"""Excepciones propias del sistema (manejo de errores claro)."""


class SistemaSanPabloError(Exception):
    """Excepción base del dominio."""


class DatoInvalidoError(SistemaSanPabloError):
    """Documento con formato inválido o datos vacíos."""


class AccesoDenegadoError(SistemaSanPabloError):
    """Perfil sin permiso para ver un dato sensible."""


class PacienteDuplicadoError(SistemaSanPabloError):
    """Ya existe un paciente con ese documento (RF-01)."""


class ConsentimientoRequeridoError(SistemaSanPabloError):
    """No se registró el consentimiento de datos personales (RF-04)."""


class CitaCruzadaError(SistemaSanPabloError):
    """La cita se cruza con otra del mismo médico o consultorio (RF-02)."""


class NoEncontradoError(SistemaSanPabloError):
    """No se encontró el paciente, médico o cita buscada."""
