"""Personal de la clínica: herencia y polimorfismo (RF-05, RF-07)."""


class Personal:
    perfil = "Personal"
    puede_ver_diagnostico = False

    def __init__(self, nombres: str):
        self.__nombres = nombres

    @property
    def nombres(self) -> str:
        return self.__nombres


class Medico(Personal):
    perfil = "Médico"
    puede_ver_diagnostico = True

    def __init__(self, nombres: str, especialidad: str):
        super().__init__(nombres)
        self.__especialidad = especialidad

    @property
    def especialidad(self) -> str:
        return self.__especialidad


class Admisionista(Personal):
    perfil = "Admisionista"


class JefeAdmision(Personal):
    perfil = "Jefe de Admisión"


class Consultorio:
    def __init__(self, codigo: str):
        self.__codigo = codigo

    @property
    def codigo(self) -> str:
        return self.__codigo
