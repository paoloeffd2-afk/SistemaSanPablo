"""Atención: herencia + polimorfismo + patrón Factory (RF-03, RD-05)."""
from abc import ABC, abstractmethod
from datetime import date


class Atencion(ABC):
    """El diagnóstico se guarda cifrado; nunca en texto plano (RD-02)."""

    tipo = "Atención"

    def __init__(self, paciente, medico, fecha: date, diagnostico: str, cifrador, costo=None):
        self.__paciente, self.__medico, self.__fecha = paciente, medico, fecha
        self.__diagnostico_cifrado = cifrador.cifrar(diagnostico)
        self.__costo = self.costo_base() if costo is None else costo
        self.__estado = "Realizada"

    paciente = property(lambda s: s.__paciente)
    medico = property(lambda s: s.__medico)
    fecha = property(lambda s: s.__fecha)
    costo = property(lambda s: s.__costo)
    estado = property(lambda s: s.__estado)
    especialidad = property(lambda s: s.__medico.especialidad)
    edad_paciente = property(lambda s: s.__paciente.edad)

    @abstractmethod
    def costo_base(self) -> float:
        """Cada tipo define su costo (polimorfismo)."""

    def diagnostico_cifrado(self) -> bytes:
        return self.__diagnostico_cifrado


class Consulta(Atencion):
    tipo = "Consulta"

    def costo_base(self) -> float:
        return 120.0


class Procedimiento(Atencion):
    tipo = "Procedimiento"

    def costo_base(self) -> float:
        return 350.0


class Interconsulta(Atencion):
    tipo = "Interconsulta"

    def costo_base(self) -> float:
        return 180.0


class AtencionFactory:
    """Crea el tipo de atención sin modificar el código existente al agregar uno nuevo."""
    _tipos = {"consulta": Consulta, "procedimiento": Procedimiento,
              "interconsulta": Interconsulta}

    @classmethod
    def registrar_tipo(cls, nombre: str, clase) -> None:
        cls._tipos[nombre.lower()] = clase

    @classmethod
    def crear(cls, tipo: str, paciente, medico, fecha, diagnostico, cifrador, costo=None):
        try:
            clase = cls._tipos[tipo.lower()]
        except KeyError:
            from excepciones import DatoInvalidoError
            raise DatoInvalidoError(f"Tipo de atención no válido: {tipo}.")
        return clase(paciente, medico, fecha, diagnostico, cifrador, costo)
