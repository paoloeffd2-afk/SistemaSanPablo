"""Pruebas pytest del módulo real SistemaSanPablo (modelos, servicios, excepciones).

Se ejecutan desde la carpeta raíz del proyecto:  python -m pytest -v
Todos los datos son ficticios (RD-03).
"""
from datetime import date, datetime, timedelta

import pytest

from excepciones import (AccesoDenegadoError, CitaCruzadaError, ConsentimientoRequeridoError,
                         DatoInvalidoError, PacienteDuplicadoError)
from modelos.atencion import AtencionFactory, Consulta, Interconsulta, Procedimiento
from modelos.paciente import Paciente
from modelos.personal import Admisionista, Consultorio, Medico
from servicios import reporte_semanal as rep
from servicios.registro_central import RegistroCentral


@pytest.fixture
def registro():
    """Singleton vacío para cada prueba."""
    reg = RegistroCentral()
    reg.reiniciar()
    return reg


@pytest.fixture
def ana():
    p = Paciente("DNI", "71234536", "ana torres", date(1990, 3, 14), "999111222", "EPS")
    p.otorgar_consentimiento()
    return p


@pytest.fixture
def medico():
    return Medico("Dr. Carlos Rojas", "Cardiología")


# ---------- Datos personales (Ley N.° 29733) ----------
def test_documento_solo_sale_enmascarado(ana):
    assert ana.documento_enmascarado == "******36"
    assert "71234536" not in repr(ana)


def test_dni_invalido_lanza_excepcion_propia():
    with pytest.raises(DatoInvalidoError):
        Paciente("DNI", "1234", "Juan Quispe", date(1985, 6, 2))


def test_registro_exige_consentimiento(registro):
    sin_consentimiento = Paciente("DNI", "71234536", "Ana Torres", date(1990, 3, 14))
    with pytest.raises(ConsentimientoRequeridoError):
        registro.registrar_paciente(sin_consentimiento)


def test_paciente_duplicado_rechazado(registro, ana):
    registro.registrar_paciente(ana)
    duplicado = Paciente("DNI", "71234536", "Ana T.", date(1990, 3, 14))
    duplicado.otorgar_consentimiento()
    with pytest.raises(PacienteDuplicadoError):
        registro.registrar_paciente(duplicado)
    assert registro.cantidad_pacientes() == 1


def test_diagnostico_se_guarda_cifrado(registro, ana, medico):
    at = AtencionFactory.crear("consulta", ana, medico, date.today(), "Hipertensión leve",
                               registro.cifrador)
    assert b"Hipertensi" not in at.diagnostico_cifrado()
    assert registro.cifrador.descifrar(at.diagnostico_cifrado()) == "Hipertensión leve"


def test_admisionista_denegado_medico_lee_y_queda_registro(registro, ana, medico):
    at = AtencionFactory.crear("consulta", ana, medico, date.today(), "Hipertensión leve",
                               registro.cifrador)
    with pytest.raises(AccesoDenegadoError):
        registro.leer_diagnostico(at, Admisionista("Rosa"))
    assert registro.leer_diagnostico(at, medico) == "Hipertensión leve"
    acciones = [a.accion for a in registro.accesos()]
    assert acciones == ["DENEGADO diagnóstico", "LEYÓ diagnóstico"]
    assert all("71234536" not in repr(a) for a in registro.accesos())  # bitácora sin DNI completo


# ---------- Patrones de diseño y polimorfismo ----------
def test_singleton_devuelve_siempre_la_misma_instancia():
    assert RegistroCentral() is RegistroCentral()


def test_factory_y_polimorfismo_de_costos(registro, ana, medico):
    esperados = {"consulta": (Consulta, 120.0), "procedimiento": (Procedimiento, 350.0),
                 "interconsulta": (Interconsulta, 180.0)}
    for tipo, (clase, costo) in esperados.items():
        at = AtencionFactory.crear(tipo, ana, medico, date.today(), "Control", registro.cifrador)
        assert isinstance(at, clase) and at.costo == costo


def test_factory_tipo_desconocido_lanza_excepcion(registro, ana, medico):
    with pytest.raises(DatoInvalidoError):
        AtencionFactory.crear("cirugia", ana, medico, date.today(), "X", registro.cifrador)


# ---------- Citas (RF-02) ----------
def test_cita_cruzada_del_mismo_medico_es_rechazada(registro, ana, medico):
    consultorio_a, consultorio_b = Consultorio("C-101"), Consultorio("C-102")
    inicio = datetime(2026, 11, 20, 9, 0)
    registro.programar_cita(ana, medico, consultorio_a, inicio)
    with pytest.raises(CitaCruzadaError):
        registro.programar_cita(ana, medico, consultorio_b, inicio + timedelta(minutes=10))
    registro.programar_cita(ana, medico, consultorio_b, inicio + timedelta(minutes=30))  # sin cruce


# ---------- Programación funcional (RF-06) ----------
def test_reporte_semanal_funcional(registro, ana, medico):
    hoy = date.today()
    lunes = hoy - timedelta(days=hoy.weekday())
    for tipo in ("consulta", "procedimiento", "interconsulta"):
        registro.registrar_atencion(
            AtencionFactory.crear(tipo, ana, medico, hoy, "Control", registro.cifrador))
    fuera = AtencionFactory.crear("consulta", ana, medico, lunes - timedelta(days=3), "Control",
                                  registro.cifrador)
    registro.registrar_atencion(fuera)

    semana = rep.atenciones_de_semana(registro.atenciones(), lunes)
    assert len(semana) == 3  # filter descarta la atención de otra semana
    assert rep.resumen_por_especialidad(semana) == {"Cardiología": 3}  # map + reduce
    assert rep.resumen_por_grupo_edad(semana) == {"Adulto (18-59)": 3}
    assert rep.ingreso_total(semana) == 120.0 + 350.0 + 180.0
