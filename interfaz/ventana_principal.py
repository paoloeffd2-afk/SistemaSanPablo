"""Interfaz gráfica por eventos con tkinter (RF-08, RD-09).

Ventana con pestañas: Pacientes, Citas, Atenciones, Reporte semanal y Accesos.
Los handlers solo llaman al RegistroCentral y a las clases del módulo; no tienen
reglas de negocio propias y muestran los errores con mensajes claros.
"""
import sys
import tkinter as tk
import traceback
from datetime import date, datetime, timedelta
from functools import wraps
from tkinter import font as tkfont
from tkinter import messagebox, simpledialog, ttk

from excepciones import DatoInvalidoError, SistemaSanPabloError
from interfaz import log_errores
from modelos.atencion import AtencionFactory
from modelos.paciente import TIPOS_ASEGURAMIENTO, TIPOS_DOCUMENTO, Paciente
from modelos.personal import Admisionista, JefeAdmision
from servicios import reporte_semanal as rep
from servicios.registro_central import RegistroCentral

TIPOS_ATENCION = ("Consulta", "Procedimiento", "Interconsulta")
FMT_FECHA, FMT_FECHA_HORA = "%Y-%m-%d", "%Y-%m-%d %H:%M"
AZUL, AZUL_CLARO, GRIS = "#0b4f8a", "#eef3f9", "#6b7280"


# ---------- utilidades de la interfaz (sin reglas de negocio) ----------
def con_errores(titulo: str):
    """Convierte los errores del dominio en un mensaje claro en vez de cerrar la ventana."""
    def decorador(funcion):
        @wraps(funcion)
        def envoltura(self, *args, **kwargs):
            try:
                return funcion(self, *args, **kwargs)
            except SistemaSanPabloError as e:
                self._estado(f"⚠ {e}")
                messagebox.showwarning(titulo, str(e), parent=self)
        return envoltura
    return decorador


def leer_fecha(texto: str, cual: str = "La fecha") -> date:
    try:
        return datetime.strptime(texto.strip(), FMT_FECHA).date()
    except ValueError:
        raise DatoInvalidoError(f"{cual} debe tener el formato AAAA-MM-DD (ej. 2026-12-01).")


def leer_fecha_hora(texto: str) -> datetime:
    try:
        return datetime.strptime(texto.strip(), FMT_FECHA_HORA)
    except ValueError:
        raise DatoInvalidoError("La fecha y hora deben tener el formato AAAA-MM-DD HH:MM (ej. 2026-12-01 09:30).")


def elegido(combo: ttk.Combobox, lista: list, que: str):
    """Devuelve el objeto elegido en el combo; evita el índice -1 cuando no se eligió nada."""
    i = combo.current()
    if i < 0 or i >= len(lista):
        raise DatoInvalidoError(f"Seleccione {que}.")
    return lista[i]


def crear_tabla(padre, columnas, altura=8):
    """Treeview con barra de desplazamiento. columnas = [(id, título, ancho)]."""
    marco = ttk.Frame(padre)
    tabla = ttk.Treeview(marco, columns=[c[0] for c in columnas], show="headings",
                         height=altura, selectmode="browse")
    for ident, titulo, ancho in columnas:
        tabla.heading(ident, text=titulo)
        tabla.column(ident, width=ancho, anchor="w")
    barra = ttk.Scrollbar(marco, orient="vertical", command=tabla.yview)
    tabla.configure(yscrollcommand=barra.set)
    tabla.pack(side="left", fill="both", expand=True)
    barra.pack(side="right", fill="y")
    tabla.tag_configure("par", background=AZUL_CLARO)
    return marco, tabla


def llenar(tabla: ttk.Treeview, filas: list) -> None:
    tabla.delete(*tabla.get_children())
    for i, fila in enumerate(filas):
        tabla.insert("", "end", iid=str(i), values=fila, tags=("par",) if i % 2 else ())


def etiqueta_paciente(p) -> str:
    return f"{p.nombres} · {p.tipo_documento} {p.documento_enmascarado}"


# ---------- ventana principal ----------
class VentanaPrincipal(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SistemaSanPablo v1.0 - Admisión Ambulatoria y Citas")
        self.geometry("1020x700")
        self.minsize(940, 620)
        self.registro = RegistroCentral()
        self.usuarios = [*self.registro.medicos(), Admisionista("Rosa Quispe"),
                         JefeAdmision("Jorge Díaz")]
        self.usuario = self.usuarios[len(self.registro.medicos())]  # arranca como Admisionista
        self._pacientes, self._citas, self._atenciones = [], [], []
        self.report_callback_exception = self._error_inesperado
        self._estilo()
        self._crear_cabecera()
        self.barra = ttk.Label(self, anchor="w", relief="sunken", padding=(8, 3))
        self.barra.pack(fill="x", side="bottom")  # antes del Notebook para que siempre se vea
        self.notas = ttk.Notebook(self)
        self.notas.pack(fill="both", expand=True, padx=10, pady=(8, 6))
        self._crear_pestana_pacientes()
        self._crear_pestana_citas()
        self._crear_pestana_atenciones()
        self._crear_pestana_reporte()
        self._crear_pestana_accesos()
        self.notas.bind("<<NotebookTabChanged>>", lambda e: self._refrescar_todo())
        self._estado("Listo. Registre un paciente para comenzar.")
        self._refrescar_todo()
        self._traer_al_frente()

    # ---------- apariencia ----------
    def _estilo(self):
        estilo = ttk.Style(self)
        if sys.platform != "win32" and "clam" in estilo.theme_names():
            estilo.theme_use("clam")
        base = tkfont.nametofont("TkDefaultFont")
        base.configure(family="Segoe UI" if sys.platform == "win32" else base.actual("family"), size=10)
        self.option_add("*Font", base)
        estilo.configure("Treeview", rowheight=26)
        estilo.configure("Treeview.Heading", font=(base.actual("family"), 10, "bold"))
        estilo.configure("TNotebook.Tab", padding=(16, 7))
        estilo.configure("Accion.TButton", font=(base.actual("family"), 10, "bold"), padding=(10, 5))
        estilo.configure("Total.TLabel", font=(base.actual("family"), 16, "bold"), foreground=AZUL)

    def _traer_al_frente(self):
        """Evita que la ventana quede escondida detrás de la consola."""
        self.lift()
        self.attributes("-topmost", True)
        self.after(400, lambda: self.attributes("-topmost", False))
        self.focus_force()

    def _crear_cabecera(self):
        cab = tk.Frame(self, bg=AZUL)
        cab.pack(fill="x")
        tk.Label(cab, text="SistemaSanPablo", bg=AZUL, fg="white",
                 font=("Segoe UI", 16, "bold")).pack(side="left", padx=14, pady=10)
        tk.Label(cab, text="Admisión ambulatoria y citas", bg=AZUL, fg="#cfe0f3").pack(side="left")
        derecha = tk.Frame(cab, bg=AZUL)
        derecha.pack(side="right", padx=14)
        tk.Label(derecha, text="Usuario actual:", bg=AZUL, fg="white").pack(side="left", padx=(0, 6))
        self.c_usuario = ttk.Combobox(derecha, state="readonly", width=34,
                                      values=[f"{u.nombres} ({u.perfil})" for u in self.usuarios])
        self.c_usuario.current(self.usuarios.index(self.usuario))
        self.c_usuario.pack(side="left")
        self.c_usuario.bind("<<ComboboxSelected>>", self.on_cambiar_usuario)

    def _estado(self, texto: str):
        self.barra.config(text=texto)

    def on_cambiar_usuario(self, _evento=None):
        self.usuario = self.usuarios[self.c_usuario.current()]
        ver = "puede" if self.usuario.puede_ver_diagnostico else "NO puede"
        self._estado(f"Usuario: {self.usuario.nombres} ({self.usuario.perfil}) - {ver} ver diagnósticos.")

    def _error_inesperado(self, tipo, valor, tb):
        detalle = "".join(traceback.format_exception(tipo, valor, tb))
        ruta = log_errores.guardar(detalle)
        extra = f"\n\nDetalle guardado en:\n{ruta}" if ruta else ""
        messagebox.showerror("Error inesperado", f"{tipo.__name__}: {valor}{extra}", parent=self)

    # ================= pestaña PACIENTES (RF-01, RF-04) =================
    def _crear_pestana_pacientes(self):
        pestana = ttk.Frame(self.notas, padding=10)
        self.notas.add(pestana, text="  Pacientes  ")
        marco = ttk.LabelFrame(pestana, text="Registrar o buscar paciente", padding=10)
        marco.pack(fill="x")
        self.v_tipo, self.v_doc = tk.StringVar(value="DNI"), tk.StringVar()
        self.v_nombres, self.v_nac, self.v_tel = tk.StringVar(), tk.StringVar(), tk.StringVar()
        self.v_seguro, self.v_consiente = tk.StringVar(value="PARTICULAR"), tk.BooleanVar()
        campos = [("Tipo de documento", ttk.Combobox(marco, textvariable=self.v_tipo, values=TIPOS_DOCUMENTO,
                                                     state="readonly", width=18)),
                  ("Número de documento", ttk.Entry(marco, textvariable=self.v_doc, width=22)),
                  ("Nombres y apellidos", ttk.Entry(marco, textvariable=self.v_nombres, width=36)),
                  ("Nacimiento (AAAA-MM-DD)", ttk.Entry(marco, textvariable=self.v_nac, width=22)),
                  ("Teléfono", ttk.Entry(marco, textvariable=self.v_tel, width=22)),
                  ("Aseguramiento", ttk.Combobox(marco, textvariable=self.v_seguro, values=TIPOS_ASEGURAMIENTO,
                                                 state="readonly", width=22))]
        for i, (texto, widget) in enumerate(campos):
            ttk.Label(marco, text=texto).grid(row=i // 2, column=(i % 2) * 2, sticky="e", padx=(8, 6), pady=4)
            widget.grid(row=i // 2, column=(i % 2) * 2 + 1, sticky="w", pady=4)
        ttk.Checkbutton(marco, variable=self.v_consiente,
                        text="El paciente autoriza el tratamiento de sus datos personales (Ley N.° 29733)"
                        ).grid(row=3, column=0, columnspan=4, sticky="w", padx=8, pady=(6, 2))
        botones = ttk.Frame(marco)
        botones.grid(row=4, column=0, columnspan=4, sticky="w", padx=8, pady=(6, 0))
        ttk.Button(botones, text="Registrar paciente", style="Accion.TButton",
                   command=self.on_registrar_paciente).pack(side="left")
        ttk.Button(botones, text="Buscar por documento", command=self.on_buscar).pack(side="left", padx=8)
        ttk.Button(botones, text="Limpiar", command=self._limpiar_formulario).pack(side="left")

        ttk.Label(pestana, text="Pacientes registrados (el documento se muestra enmascarado)",
                  foreground=GRIS).pack(anchor="w", pady=(10, 2))
        marco_t, self.t_pacientes = crear_tabla(pestana, [
            ("tipo", "Tipo", 70), ("doc", "Documento", 110), ("nombres", "Nombres", 280),
            ("edad", "Edad", 60), ("seguro", "Aseguramiento", 150), ("consent", "Consentimiento", 120)], 6)
        marco_t.pack(fill="both", expand=True)
        self.t_pacientes.bind("<<TreeviewSelect>>", self.on_seleccionar_paciente)
        hist = ttk.LabelFrame(pestana, text="Historial del paciente seleccionado", padding=6)
        hist.pack(fill="x", pady=(8, 0))
        self.t_historial = tk.Text(hist, height=5, state="disabled", relief="flat", background="#fafafa")
        self.t_historial.pack(fill="x")

    @con_errores("No se pudo registrar")
    def on_registrar_paciente(self):
        nacimiento = leer_fecha(self.v_nac.get(), "La fecha de nacimiento")
        paciente = Paciente(self.v_tipo.get(), self.v_doc.get(), self.v_nombres.get(),
                            nacimiento, self.v_tel.get(), self.v_seguro.get())
        if self.v_consiente.get():
            paciente.otorgar_consentimiento()
        self.registro.registrar_paciente(paciente)
        self._estado(f"✔ Paciente registrado: {paciente}")
        self._limpiar_formulario()
        self._refrescar_todo()
        messagebox.showinfo("Registro correcto", f"Se registró a {paciente.nombres}.", parent=self)

    @con_errores("Búsqueda")
    def on_buscar(self):
        paciente = self.registro.buscar_paciente(self.v_tipo.get(), self.v_doc.get())
        self._refrescar_pacientes()
        i = next(k for k, p in enumerate(self._pacientes) if p is paciente)
        self.t_pacientes.selection_set(str(i))
        self.t_pacientes.see(str(i))
        self._estado(f"Paciente encontrado: {paciente.nombres}")

    def on_seleccionar_paciente(self, _evento=None):
        sel = self.t_pacientes.selection()
        if not sel:
            return
        paciente = self._pacientes[int(sel[0])]
        lineas = self.registro.historial_de(paciente, self.usuario)
        self.t_historial.config(state="normal")
        self.t_historial.delete("1.0", "end")
        self.t_historial.insert("end", "\n".join(lineas) if lineas else "Sin citas ni atenciones.")
        self.t_historial.config(state="disabled")

    def _limpiar_formulario(self):
        for v in (self.v_doc, self.v_nombres, self.v_nac, self.v_tel):
            v.set("")
        self.v_tipo.set("DNI")
        self.v_seguro.set("PARTICULAR")
        self.v_consiente.set(False)

    # ================= pestaña CITAS (RF-02) =================
    def _crear_pestana_citas(self):
        pestana = ttk.Frame(self.notas, padding=10)
        self.notas.add(pestana, text="  Citas  ")
        marco = ttk.LabelFrame(pestana, text="Programar cita", padding=10)
        marco.pack(fill="x")
        self.c_cita_pac = ttk.Combobox(marco, state="readonly", width=30)
        self.c_cita_med = ttk.Combobox(marco, state="readonly", width=28,
                                       values=[f"{m.nombres} - {m.especialidad}" for m in self.registro.medicos()])
        self.c_cita_con = ttk.Combobox(marco, state="readonly", width=12,
                                       values=[c.codigo for c in self.registro.consultorios()])
        manana = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
        self.v_cita_fecha = tk.StringVar(value=f"{manana:{FMT_FECHA_HORA}}")
        self.c_cita_dur = ttk.Combobox(marco, state="readonly", width=8, values=("15", "30", "45", "60"))
        self.c_cita_dur.set("30")
        filas = [("Paciente", self.c_cita_pac, "Médico", self.c_cita_med),
                 ("Consultorio", self.c_cita_con, "Fecha y hora (AAAA-MM-DD HH:MM)",
                  ttk.Entry(marco, textvariable=self.v_cita_fecha, width=22)),
                 ("Duración (min)", self.c_cita_dur, None, None)]
        for r, (t1, w1, t2, w2) in enumerate(filas):
            ttk.Label(marco, text=t1).grid(row=r, column=0, sticky="e", padx=(8, 6), pady=4)
            w1.grid(row=r, column=1, sticky="w", pady=4)
            if t2:
                ttk.Label(marco, text=t2).grid(row=r, column=2, sticky="e", padx=(16, 6), pady=4)
                w2.grid(row=r, column=3, sticky="w", pady=4)
        ttk.Button(marco, text="Programar cita", style="Accion.TButton",
                   command=self.on_programar_cita).grid(row=2, column=3, sticky="w", pady=4)

        acciones = ttk.Frame(pestana)
        acciones.pack(fill="x", pady=(10, 2))
        ttk.Label(acciones, text="Citas programadas", foreground=GRIS).pack(side="left")
        ttk.Button(acciones, text="Cancelar cita seleccionada", command=self.on_cancelar_cita).pack(side="right")
        ttk.Button(acciones, text="Reprogramar seleccionada", command=self.on_reprogramar_cita).pack(side="right", padx=8)
        marco_t, self.t_citas = crear_tabla(pestana, [
            ("fecha", "Fecha y hora", 140), ("pac", "Paciente", 230), ("med", "Médico", 190),
            ("con", "Consultorio", 90), ("est", "Estado", 100)], 10)
        marco_t.pack(fill="both", expand=True)

    @con_errores("No se pudo programar")
    def on_programar_cita(self):
        paciente = elegido(self.c_cita_pac, self._pacientes, "un paciente (regístrelo antes en la pestaña Pacientes)")
        medico = elegido(self.c_cita_med, self.registro.medicos(), "un médico")
        consultorio = elegido(self.c_cita_con, self.registro.consultorios(), "un consultorio")
        inicio = leer_fecha_hora(self.v_cita_fecha.get())
        cita = self.registro.programar_cita(paciente, medico, consultorio, inicio, int(self.c_cita_dur.get()))
        self._estado(f"✔ Cita programada: {cita}")
        self._refrescar_citas()

    def _cita_seleccionada(self):
        sel = self.t_citas.selection()
        if not sel:
            raise DatoInvalidoError("Seleccione primero una cita de la tabla.")
        return self._citas[int(sel[0])]

    @con_errores("No se pudo reprogramar")
    def on_reprogramar_cita(self):
        cita = self._cita_seleccionada()
        if cita.estado != cita.PROGRAMADA:
            raise DatoInvalidoError("Solo se pueden reprogramar citas en estado Programada.")
        texto = simpledialog.askstring("Reprogramar cita", "Nueva fecha y hora (AAAA-MM-DD HH:MM):",
                                       initialvalue=f"{cita.inicio:{FMT_FECHA_HORA}}", parent=self)
        if texto is None:
            return
        self.registro.reprogramar_cita(cita, leer_fecha_hora(texto))
        self._estado("✔ Cita reprogramada.")
        self._refrescar_citas()

    @con_errores("No se pudo cancelar")
    def on_cancelar_cita(self):
        cita = self._cita_seleccionada()
        if messagebox.askyesno("Cancelar cita", f"¿Cancelar la cita del {cita.inicio:%d/%m/%Y %H:%M}?", parent=self):
            self.registro.cancelar_cita(cita)
            self._estado("✔ Cita cancelada.")
            self._refrescar_citas()

    # ================= pestaña ATENCIONES (RF-03, RF-07) =================
    def _crear_pestana_atenciones(self):
        pestana = ttk.Frame(self.notas, padding=10)
        self.notas.add(pestana, text="  Atenciones  ")
        marco = ttk.LabelFrame(pestana, text="Registrar atención (el diagnóstico se guarda cifrado)", padding=10)
        marco.pack(fill="x")
        self.c_at_pac = ttk.Combobox(marco, state="readonly", width=34)
        self.c_at_tipo = ttk.Combobox(marco, state="readonly", width=16, values=TIPOS_ATENCION)
        self.c_at_tipo.current(0)
        self.c_at_med = ttk.Combobox(marco, state="readonly", width=34,
                                     values=[f"{m.nombres} - {m.especialidad}" for m in self.registro.medicos()])
        self.v_at_fecha = tk.StringVar(value=f"{date.today():{FMT_FECHA}}")
        self.t_at_diag = tk.Text(marco, height=3, width=60)
        for r, (t1, w1, t2, w2) in enumerate([
                ("Paciente", self.c_at_pac, "Tipo", self.c_at_tipo),
                ("Médico", self.c_at_med, "Fecha (AAAA-MM-DD)", ttk.Entry(marco, textvariable=self.v_at_fecha, width=18))]):
            ttk.Label(marco, text=t1).grid(row=r, column=0, sticky="e", padx=(8, 6), pady=4)
            w1.grid(row=r, column=1, sticky="w", pady=4)
            ttk.Label(marco, text=t2).grid(row=r, column=2, sticky="e", padx=(16, 6), pady=4)
            w2.grid(row=r, column=3, sticky="w", pady=4)
        ttk.Label(marco, text="Diagnóstico").grid(row=2, column=0, sticky="ne", padx=(8, 6), pady=4)
        self.t_at_diag.grid(row=2, column=1, columnspan=3, sticky="w", pady=4)
        ttk.Button(marco, text="Registrar atención", style="Accion.TButton",
                   command=self.on_registrar_atencion).grid(row=3, column=1, sticky="w", pady=4)

        acciones = ttk.Frame(pestana)
        acciones.pack(fill="x", pady=(10, 2))
        ttk.Label(acciones, text="Atenciones realizadas", foreground=GRIS).pack(side="left")
        ttk.Button(acciones, text="Ver diagnóstico (según el usuario actual)",
                   command=self.on_ver_diagnostico).pack(side="right")
        marco_t, self.t_atenciones = crear_tabla(pestana, [
            ("fecha", "Fecha", 100), ("tipo", "Tipo", 110), ("pac", "Paciente", 230),
            ("esp", "Especialidad", 150), ("costo", "Costo", 90), ("diag", "Diagnóstico", 120)], 9)
        marco_t.pack(fill="both", expand=True)

    @con_errores("No se pudo registrar la atención")
    def on_registrar_atencion(self):
        paciente = elegido(self.c_at_pac, self._pacientes, "un paciente")
        medico = elegido(self.c_at_med, self.registro.medicos(), "un médico")
        fecha = leer_fecha(self.v_at_fecha.get())
        diagnostico = self.t_at_diag.get("1.0", "end").strip()
        if not diagnostico:
            raise DatoInvalidoError("Escriba el diagnóstico.")
        atencion = AtencionFactory.crear(self.c_at_tipo.get(), paciente, medico, fecha,
                                         diagnostico, self.registro.cifrador)
        self.registro.registrar_atencion(atencion)
        self.t_at_diag.delete("1.0", "end")
        self._estado(f"✔ {atencion.tipo} registrada (S/ {atencion.costo:.2f}).")
        self._refrescar_atenciones()

    @con_errores("Diagnóstico")
    def on_ver_diagnostico(self):
        sel = self.t_atenciones.selection()
        if not sel:
            raise DatoInvalidoError("Seleccione primero una atención de la tabla.")
        atencion = self._atenciones[int(sel[0])]
        try:
            texto = self.registro.leer_diagnostico(atencion, self.usuario)
        finally:
            self._refrescar_accesos()  # el intento (permitido o denegado) queda registrado
        messagebox.showinfo("Diagnóstico",
                            f"Paciente: {atencion.paciente.nombres}\n{atencion.tipo} del {atencion.fecha:%d/%m/%Y}"
                            f"\n\n{texto}", parent=self)

    # ================= pestaña REPORTE SEMANAL (RF-06) =================
    def _crear_pestana_reporte(self):
        pestana = ttk.Frame(self.notas, padding=10)
        self.notas.add(pestana, text="  Reporte semanal  ")
        barra = ttk.Frame(pestana)
        barra.pack(fill="x")
        self.v_lunes = tk.StringVar(value=f"{self._lunes_de(date.today()):{FMT_FECHA}}")
        ttk.Label(barra, text="Semana que inicia el lunes").pack(side="left")
        ttk.Button(barra, text="◀", width=3, command=lambda: self._mover_semana(-7)).pack(side="left", padx=(8, 2))
        ttk.Entry(barra, textvariable=self.v_lunes, width=12).pack(side="left")
        ttk.Button(barra, text="▶", width=3, command=lambda: self._mover_semana(7)).pack(side="left", padx=2)
        ttk.Button(barra, text="Generar reporte", style="Accion.TButton",
                   command=self._refrescar_reporte).pack(side="left", padx=12)
        self.l_rango = ttk.Label(barra, foreground=GRIS)
        self.l_rango.pack(side="left")
        cuerpo = ttk.Frame(pestana)
        cuerpo.pack(fill="both", expand=True, pady=10)
        izq = ttk.LabelFrame(cuerpo, text="Atenciones por especialidad", padding=6)
        der = ttk.LabelFrame(cuerpo, text="Atenciones por grupo de edad", padding=6)
        izq.pack(side="left", fill="both", expand=True, padx=(0, 6))
        der.pack(side="left", fill="both", expand=True, padx=(6, 0))
        m1, self.t_rep_esp = crear_tabla(izq, [("k", "Especialidad", 220), ("n", "Atenciones", 90)], 10)
        m2, self.t_rep_edad = crear_tabla(der, [("k", "Grupo de edad", 220), ("n", "Atenciones", 90)], 10)
        m1.pack(fill="both", expand=True)
        m2.pack(fill="both", expand=True)
        self.l_total = ttk.Label(pestana, style="Total.TLabel")
        self.l_total.pack(anchor="e")

    @staticmethod
    def _lunes_de(dia: date) -> date:
        return dia - timedelta(days=dia.weekday())

    def _mover_semana(self, dias: int):
        try:
            lunes = self._lunes_de(leer_fecha(self.v_lunes.get())) + timedelta(days=dias)
        except DatoInvalidoError:
            lunes = self._lunes_de(date.today())
        self.v_lunes.set(f"{lunes:{FMT_FECHA}}")
        self._refrescar_reporte()

    @con_errores("Reporte semanal")
    def _refrescar_reporte(self):
        lunes = self._lunes_de(leer_fecha(self.v_lunes.get(), "La fecha del lunes"))
        self.v_lunes.set(f"{lunes:{FMT_FECHA}}")
        semana = rep.atenciones_de_semana(self.registro.atenciones(), lunes)
        llenar(self.t_rep_esp, sorted(rep.resumen_por_especialidad(semana).items()))
        llenar(self.t_rep_edad, sorted(rep.resumen_por_grupo_edad(semana).items()))
        domingo = lunes + timedelta(days=6)
        self.l_rango.config(text=f"{lunes:%d/%m/%Y} al {domingo:%d/%m/%Y} · {len(semana)} atenciones")
        self.l_total.config(text=f"Ingreso total de la semana: S/ {rep.ingreso_total(semana):,.2f}")

    # ================= pestaña ACCESOS (RF-07) =================
    def _crear_pestana_accesos(self):
        pestana = ttk.Frame(self.notas, padding=10)
        self.notas.add(pestana, text="  Registro de accesos  ")
        ttk.Label(pestana, foreground=GRIS,
                  text="Cada consulta o intento de ver un diagnóstico queda registrado (documento enmascarado)."
                  ).pack(anchor="w", pady=(0, 4))
        marco_t, self.t_accesos = crear_tabla(pestana, [
            ("fecha", "Fecha y hora", 150), ("perfil", "Perfil", 140),
            ("accion", "Acción", 220), ("doc", "Documento", 120)], 16)
        marco_t.pack(fill="both", expand=True)

    # ---------- refrescos ----------
    def _refrescar_todo(self):
        self._refrescar_pacientes()
        self._refrescar_citas()
        self._refrescar_atenciones()
        self._refrescar_accesos()
        self._refrescar_reporte()

    def _refrescar_pacientes(self):
        self._pacientes = self.registro.pacientes()
        llenar(self.t_pacientes, [(p.tipo_documento, p.documento_enmascarado, p.nombres, p.edad,
                                   p.aseguramiento, "Sí" if p.tiene_consentimiento else "No")
                                  for p in self._pacientes])
        etiquetas = [etiqueta_paciente(p) for p in self._pacientes]
        for combo in (self.c_cita_pac, self.c_at_pac):
            combo.config(values=etiquetas)

    def _refrescar_citas(self):
        self._citas = sorted(self.registro.citas(), key=lambda c: c.inicio)
        llenar(self.t_citas, [(f"{c.inicio:%d/%m/%Y %H:%M}", c.paciente.nombres, c.medico.nombres,
                               c.consultorio.codigo, c.estado) for c in self._citas])

    def _refrescar_atenciones(self):
        self._atenciones = self.registro.atenciones()
        llenar(self.t_atenciones, [(f"{a.fecha:%d/%m/%Y}", a.tipo, a.paciente.nombres, a.especialidad,
                                    f"S/ {a.costo:.2f}", "🔒 cifrado") for a in self._atenciones])
        self._refrescar_accesos()

    def _refrescar_accesos(self):
        llenar(self.t_accesos, [(f"{a.fecha:%d/%m/%Y %H:%M:%S}", a.perfil, a.accion, a.documento)
                                for a in reversed(self.registro.accesos())])
