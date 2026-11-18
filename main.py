"""Punto de entrada.

  python main.py           -> abre la ventana (interfaz gráfica)
  python main.py --consola -> demostración en consola (RF-01 a RF-07, datos ficticios)

Si algo falla al arrancar, se muestra una ventana con el motivo y se guarda error.log
(la consola ya no se cierra sola sin decir nada).
"""
import os
import subprocess
import sys
import traceback
from datetime import date, datetime, timedelta

# Permite ejecutar desde cualquier carpeta (doble clic, Visual Studio, otra terminal).
RAIZ = os.path.dirname(os.path.abspath(__file__))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.chdir(RAIZ)

from datos_demo import cargar_catalogo  # noqa: E402
from excepciones import SistemaSanPabloError  # noqa: E402
from modelos.atencion import AtencionFactory  # noqa: E402
from modelos.paciente import Paciente  # noqa: E402
from modelos.personal import Admisionista  # noqa: E402
from servicios import reporte_semanal as rep  # noqa: E402
from servicios.entorno import cargar_env  # noqa: E402

__version__ = "1.0.0"
cargar_env(os.path.join(RAIZ, ".env"))  # clave de cifrado local (no se sube a Git)


def demo_consola():
    registro = cargar_catalogo()
    medico, consultorio = registro.medicos()[0], registro.consultorios()[0]
    ana = Paciente("DNI", "71234536", "ana torres", date(1990, 3, 14), "999111222", "EPS")
    try:
        registro.registrar_paciente(ana)
    except SistemaSanPabloError as e:
        print("RF-04 sin consentimiento ->", e)
    ana.otorgar_consentimiento()
    registro.registrar_paciente(ana)
    print("RF-01 registrado:", ana)
    try:
        dup = Paciente("DNI", "71234536", "Ana T.", date(1990, 3, 14))
        dup.otorgar_consentimiento()
        registro.registrar_paciente(dup)
    except SistemaSanPabloError as e:
        print("RF-01 duplicado  ->", e)

    inicio = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
    print("RF-02", registro.programar_cita(ana, medico, consultorio, inicio))
    try:
        registro.programar_cita(ana, medico, consultorio, inicio + timedelta(minutes=10))
    except SistemaSanPabloError as e:
        print("RF-02 cruce      ->", e)

    for tipo in ("consulta", "procedimiento", "interconsulta"):
        registro.registrar_atencion(AtencionFactory.crear(
            tipo, ana, medico, date.today(), "Hipertensión leve", registro.cifrador))
    at = registro.atenciones()[0]
    try:
        registro.leer_diagnostico(at, Admisionista("Rosa"))
    except SistemaSanPabloError as e:
        print("RF-07 admisionista ->", e)
    print("RF-07 médico lee   ->", registro.leer_diagnostico(at, medico))
    print("RF-07 historial    ->", registro.historial("DNI", "71234536", medico))
    lunes = date.today() - timedelta(days=date.today().weekday())
    semana = rep.atenciones_de_semana(registro.atenciones(), lunes)
    print("RF-06 por especialidad:", rep.resumen_por_especialidad(semana))
    print("RF-06 por grupo edad  :", rep.resumen_por_grupo_edad(semana))
    print("RF-06 ingreso total   : S/", rep.ingreso_total(semana))
    print("Registro de accesos:")
    for a in registro.accesos():
        print("  ", a)


def _avisar(titulo: str, mensaje: str, error: bool = True) -> None:
    """Muestra un mensaje en ventana; si no se puede, lo imprime y espera una tecla."""
    print(f"\n[{titulo}]\n{mensaje}")
    try:
        import tkinter as tk
        from tkinter import messagebox
        raiz = tk.Tk()
        raiz.withdraw()
        raiz.attributes("-topmost", True)
        (messagebox.showerror if error else messagebox.showinfo)(titulo, mensaje, parent=raiz)
        raiz.destroy()
    except Exception:
        if sys.stdin and sys.stdin.isatty():
            input("\nPresione Enter para cerrar...")


def _asegurar_cryptography() -> bool:
    """Si falta 'cryptography' ofrece instalarlo en el mismo Python que ejecuta el programa."""
    try:
        import cryptography  # noqa: F401
        return True
    except ImportError:
        pass
    try:
        import tkinter as tk
        from tkinter import messagebox
        raiz = tk.Tk()
        raiz.withdraw()
        raiz.attributes("-topmost", True)
        instalar = messagebox.askyesno(
            "Falta un componente",
            "Falta instalar el paquete 'cryptography' (cifrado de diagnósticos).\n\n"
            "¿Instalarlo ahora? Necesita conexión a internet y tarda unos segundos.", parent=raiz)
        raiz.destroy()
    except Exception:
        instalar = True
    if not instalar:
        return False
    resultado = subprocess.run([sys.executable, "-m", "pip", "install", "cryptography"])
    if resultado.returncode != 0:
        _avisar("No se pudo instalar",
                f"Ejecute manualmente en una terminal:\n\n{sys.executable} -m pip install cryptography")
        return False
    return True


def iniciar_gui() -> int:
    try:
        import tkinter  # noqa: F401
    except ImportError:
        _avisar("Falta tkinter",
                "Esta instalación de Python no incluye tkinter (la librería de ventanas).\n\n"
                "Ejecute el instalador de Python otra vez, elija Modify y marque 'tcl/tk and IDLE'.")
        return 1
    if not _asegurar_cryptography():
        return 1
    from interfaz.ventana_principal import VentanaPrincipal
    cargar_catalogo()
    VentanaPrincipal().mainloop()
    return 0


def main() -> int:
    if "--consola" in sys.argv:
        demo_consola()
        return 0
    return iniciar_gui()


if __name__ == "__main__":
    try:
        codigo = main()
    except Exception:
        detalle = traceback.format_exc()
        try:
            from interfaz.log_errores import guardar
            ruta = guardar(detalle)
        except Exception:
            ruta = ""
        _avisar("SistemaSanPablo no pudo iniciar",
                f"{detalle.strip().splitlines()[-1]}\n\n" + (f"Detalle completo en:\n{ruta}" if ruta else detalle))
        codigo = 1
    sys.exit(codigo)
