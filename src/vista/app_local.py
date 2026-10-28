"""Vista local Tkinter: ejecuta y reproduce corridas reales de ``MotorDES``.

No contiene otro simulador. Cada fotograma se reconstruye desde los eventos de
``ResultadoCorrida`` mediante el tablero D2 existente.
"""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk

from src.modelo.motor_des import MotorDES
from src.modelo.parametros import ParametrosEscenario, Unidad
from src.modelo.resultados import Disciplina, ResultadoCorrida, TipoEvento
from src.vista.animacion import EstadoTablero, reconstruir_tablero

VERDE, AZUL, TINTA = "#0f795e", "#3957c8", "#17312c"
PAPEL, SUPERFICIE, MUTED = "#f5f2e9", "#fffdf7", "#63706b"


@dataclass(frozen=True)
class ConfiguracionVista:
    llegadas_hora: float
    servicios_hora: float
    cajeros: int
    proporcion_preferencial: float
    horizonte_minutos: float
    semilla: int
    disciplina: Disciplina

    def validar(self) -> None:
        if not 1 <= self.llegadas_hora <= 1000:
            raise ValueError("Las llegadas deben estar entre 1 y 1000 por hora.")
        if not 1 <= self.servicios_hora <= 300:
            raise ValueError("La atención debe estar entre 1 y 300 por hora y cajero.")
        if not 1 <= self.cajeros <= 24:
            raise ValueError("La cantidad de cajeros debe estar entre 1 y 24.")
        if not 0 <= self.proporcion_preferencial <= 1:
            raise ValueError("La proporción preferencial debe estar entre 0 y 1.")
        if not 1 <= self.horizonte_minutos <= 1440:
            raise ValueError("El horizonte debe estar entre 1 y 1440 minutos.")
        if self.semilla < 0:
            raise ValueError("La semilla debe ser un entero no negativo.")


def crear_parametros(config: ConfiguracionVista) -> ParametrosEscenario:
    """Convierte las tasas visibles por hora a las tasas/minuto del motor."""
    config.validar()
    return ParametrosEscenario(
        nombre="vista_local_personalizada", unidad=Unidad.MINUTO,
        lam=config.llegadas_hora / 60, mu=config.servicios_hora / 60,
        c=config.cajeros, p=config.proporcion_preferencial,
        origen_p="supuesto experimental ingresado en la vista local",
        horizon=config.horizonte_minutos, warmup=0, seed=config.semilla,
    )


def ejecutar_simulacion(config: ConfiguracionVista) -> ResultadoCorrida:
    parametros = crear_parametros(config)
    return MotorDES(parametros, config.disciplina, semilla=config.semilla).correr()


class AplicacionSimulacion(tk.Tk):
    """Panel de parámetros y replay de eventos del backend Python."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Fila Viva · Simulación bancaria M/M/c")
        self.geometry("1180x760")
        self.minsize(920, 620)
        self.configure(bg=PAPEL)
        self.resultado: ResultadoCorrida | None = None
        self.instante, self.en_reproduccion, self._after_id = 0.0, False, None
        self._estilos()
        self._variables()
        self._interfaz()

    def _estilos(self) -> None:
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("Panel.TFrame", background=SUPERFICIE)
        s.configure("Sala.TFrame", background=PAPEL)
        s.configure("Titulo.TLabel", background=SUPERFICIE, foreground=TINTA,
                    font=("TkDefaultFont", 22, "bold"))
        s.configure("Texto.TLabel", background=SUPERFICIE, foreground=MUTED)
        s.configure("Campo.TLabel", background=SUPERFICIE, foreground=VERDE,
                    font=("TkDefaultFont", 9, "bold"))
        s.configure("Accent.TButton", background=VERDE, foreground="white", padding=10)
        s.configure("Treeview", rowheight=28)
        s.configure("Treeview.Heading", background=TINTA, foreground="white")

    def _variables(self) -> None:
        self.llegadas, self.servicio = tk.DoubleVar(value=18), tk.DoubleVar(value=12)
        self.cajeros, self.p = tk.IntVar(value=3), tk.DoubleVar(value=30)
        self.horizonte, self.semilla = tk.DoubleVar(value=120), tk.IntVar(value=12345)
        self.disciplina, self.velocidad = tk.StringVar(value="prioridad"), tk.DoubleVar(value=10)
        self.reloj, self.estado = tk.StringVar(value="00:00"), tk.StringVar(value="Lista")
        self.metricas = tk.StringVar(value="Ejecuta una corrida para ver resultados")

    def _interfaz(self) -> None:
        top = tk.Frame(self, bg=TINTA, height=62)
        top.pack(fill="x"); top.pack_propagate(False)
        tk.Label(top, text="FILA VIVA · PYTHON", bg=TINTA, fg="white",
                 font=("TkDefaultFont", 15, "bold")).pack(side="left", padx=22)
        tk.Label(top, textvariable=self.estado, bg=TINTA, fg="#68d8b2").pack(side="right", padx=22)
        pane = ttk.Panedwindow(self, orient="horizontal"); pane.pack(fill="both", expand=True)
        panel, sala = ttk.Frame(pane, style="Panel.TFrame", width=310), ttk.Frame(pane, style="Sala.TFrame")
        pane.add(panel, weight=0); pane.add(sala, weight=1)
        self._panel(panel); self._sala(sala)

    def _panel(self, panel) -> None:
        ttk.Label(panel, text="Diseña el flujo\nde tu banco.", style="Titulo.TLabel").pack(
            anchor="w", padx=22, pady=(24, 4))
        ttk.Label(panel, text="Estos valores se envían directamente a MotorDES.",
                  style="Texto.TLabel", wraplength=260).pack(anchor="w", padx=22)
        form = ttk.Frame(panel, style="Panel.TFrame"); form.pack(fill="both", expand=True, padx=22, pady=12)
        self._numero(form, "Llegadas λ (clientes/h)", self.llegadas, 1, 1000)
        self._numero(form, "Atención μ (clientes/h/cajero)", self.servicio, 1, 300)
        self._numero(form, "Cajeros compartidos", self.cajeros, 1, 24)
        ttk.Label(form, text="Proporción preferencial", style="Campo.TLabel").pack(anchor="w", pady=(10, 2))
        pf = ttk.Frame(form, style="Panel.TFrame"); pf.pack(fill="x")
        ttk.Scale(pf, from_=0, to=100, variable=self.p,
                  command=lambda _: self.p_texto.config(text=f"{self.p.get():.0f}%"))\
            .pack(side="left", fill="x", expand=True)
        self.p_texto = ttk.Label(pf, text="30%", style="Campo.TLabel", width=5); self.p_texto.pack(side="right")
        self._numero(form, "Horizonte (minutos)", self.horizonte, 1, 1440)
        self._numero(form, "Semilla", self.semilla, 0, 2_147_483_647)
        ttk.Label(form, text="Disciplina", style="Campo.TLabel").pack(anchor="w", pady=(10, 2))
        radios = ttk.Frame(form, style="Panel.TFrame"); radios.pack(fill="x")
        ttk.Radiobutton(radios, text="Prioridad", variable=self.disciplina,
                        value="prioridad").pack(side="left")
        ttk.Radiobutton(radios, text="FCFS", variable=self.disciplina,
                        value="fcfs").pack(side="left", padx=12)
        ttk.Label(form, text="Velocidad del replay", style="Campo.TLabel").pack(anchor="w", pady=(10, 2))
        ttk.Combobox(form, textvariable=self.velocidad, state="readonly",
                     values=(1, 5, 10, 30, 60)).pack(fill="x")
        buttons = ttk.Frame(form, style="Panel.TFrame"); buttons.pack(fill="x", pady=16)
        ttk.Button(buttons, text="Ejecutar", style="Accent.TButton",
                   command=self.ejecutar).pack(side="left", fill="x", expand=True)
        self.replay = ttk.Button(buttons, text="▶ Replay", command=self.alternar,
                                 state="disabled"); self.replay.pack(side="left", padx=(6, 0))

    @staticmethod
    def _numero(parent, label, variable, minimo, maximo) -> None:
        ttk.Label(parent, text=label, style="Campo.TLabel").pack(anchor="w", pady=(10, 2))
        ttk.Spinbox(parent, textvariable=variable, from_=minimo, to=maximo).pack(fill="x")

    def _sala(self, sala) -> None:
        header = ttk.Frame(sala, style="Sala.TFrame"); header.pack(fill="x", padx=22, pady=(18, 8))
        ttk.Label(header, text="REPLAY DE EVENTOS REALES", background=PAPEL,
                  foreground=VERDE, font=("TkDefaultFont", 9, "bold")).pack(side="left")
        ttk.Label(header, textvariable=self.reloj, background=PAPEL,
                  foreground=VERDE, font=("TkFixedFont", 20, "bold")).pack(side="right")
        tk.Label(sala, textvariable=self.metricas, bg=TINTA, fg="white",
                 anchor="w", padx=14, pady=10, font=("TkFixedFont", 9)).pack(fill="x", padx=22)
        queues = ttk.Frame(sala, style="Sala.TFrame"); queues.pack(fill="x", padx=22, pady=12)
        self.pref = self._lista(queues, "Cola preferencial", VERDE, 0)
        self.general = self._lista(queues, "Cola general", AZUL, 1)
        box = ttk.LabelFrame(sala, text="Cajeros · usa el scroll para ver los 24")
        box.pack(fill="both", expand=True, padx=22)
        self.tabla = ttk.Treeview(box, columns=("estado", "cliente"), show="headings", height=9)
        self.tabla.heading("estado", text="Módulo / estado"); self.tabla.heading("cliente", text="Cliente")
        self.tabla.column("estado", width=200, anchor="center"); self.tabla.column("cliente", width=160, anchor="center")
        sy = ttk.Scrollbar(box, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=sy.set)
        self.tabla.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        sy.pack(side="right", fill="y", padx=(0, 10), pady=10)
        self.tiempo = ttk.Scale(sala, from_=0, to=1, command=self.buscar, state="disabled")
        self.tiempo.pack(fill="x", padx=22, pady=16)

    @staticmethod
    def _lista(parent, title, color, column):
        frame = tk.LabelFrame(parent, text=title, bg=SUPERFICIE, fg=color, padx=6, pady=6)
        frame.grid(row=0, column=column, sticky="nsew", padx=4); parent.columnconfigure(column, weight=1)
        box = tk.Listbox(frame, height=4, fg=color, font=("TkFixedFont", 9))
        sx, sy = ttk.Scrollbar(frame, orient="horizontal", command=box.xview), ttk.Scrollbar(frame, orient="vertical", command=box.yview)
        box.configure(xscrollcommand=sx.set, yscrollcommand=sy.set)
        box.grid(row=0, column=0, sticky="nsew"); sy.grid(row=0, column=1, sticky="ns"); sx.grid(row=1, column=0, sticky="ew")
        frame.columnconfigure(0, weight=1)
        return box

    def _config(self) -> ConfiguracionVista:
        return ConfiguracionVista(float(self.llegadas.get()), float(self.servicio.get()),
            int(self.cajeros.get()), float(self.p.get()) / 100, float(self.horizonte.get()),
            int(self.semilla.get()), Disciplina.PRIORIDAD if self.disciplina.get() == "prioridad" else Disciplina.FCFS)

    def ejecutar(self) -> None:
        self.detener()
        try: self.resultado = ejecutar_simulacion(self._config())
        except (tk.TclError, TypeError, ValueError) as exc:
            messagebox.showerror("Parámetros inválidos", str(exc), parent=self); return
        self.instante = 0.; self.tiempo.configure(to=self.resultado.parametros.horizon, state="normal"); self.tiempo.set(0)
        self.replay.configure(state="normal"); self.estado.set(f"{len(self.resultado.clientes)} llegadas · semilla {self.resultado.semilla}")
        self.mostrar(0); self.alternar()

    def alternar(self) -> None:
        if self.resultado is None: return
        self.en_reproduccion = not self.en_reproduccion
        self.replay.configure(text="⏸ Pausar" if self.en_reproduccion else "▶ Replay")
        if self.en_reproduccion:
            if self.instante >= self.resultado.parametros.horizon: self.instante = 0
            self.programar()
        else: self.cancelar()

    def programar(self): self.cancelar(); self._after_id = self.after(80, self.tick)
    def cancelar(self):
        if self._after_id is not None: self.after_cancel(self._after_id); self._after_id = None
    def detener(self):
        self.en_reproduccion = False; self.cancelar()
        if hasattr(self, "replay"): self.replay.configure(text="▶ Replay")
    def tick(self):
        if not self.en_reproduccion or self.resultado is None: return
        self.instante = min(self.resultado.parametros.horizon,
                            self.instante + float(self.velocidad.get()) * .08)
        self.tiempo.set(self.instante); self.mostrar(self.instante)
        if self.instante >= self.resultado.parametros.horizon: self.detener()
        else: self.programar()
    def buscar(self, value):
        if self.resultado is not None: self.instante = float(value); self.mostrar(self.instante)

    def mostrar(self, t: float) -> None:
        state = reconstruir_tablero(self.resultado, t)
        minutes, seconds = int(t), int(round((t-int(t))*60)) % 60
        self.reloj.set(f"{minutes:02d}:{seconds:02d}")
        for widget, ids, prefix in ((self.pref, state.cola_preferencial, "P"),
                                    (self.general, state.cola_general, "G")):
            widget.delete(0, "end")
            for pos, cid in enumerate(ids, 1): widget.insert("end", f"{pos:02d} · {prefix}{cid}")
            if not ids: widget.insert("end", "— cola vacía —")
        self.tabla.delete(*self.tabla.get_children())
        for n, cid in enumerate(state.cajeros, 1):
            self.tabla.insert("", "end", values=(f"Cajero {n:02d} · " + ("OCUPADO" if cid is not None else "LIBRE"),
                                                   f"Cliente {cid}" if cid is not None else "—"))
        events = [e for e in self.resultado.eventos if e.instante <= t]
        arrived = sum(e.tipo is TipoEvento.LLEGADA for e in events)
        served = sum(e.tipo is TipoEvento.FIN_SERVICIO for e in events)
        started = [c for c in self.resultado.clientes if c.t_inicio_servicio is not None and c.t_inicio_servicio <= t]
        wait = sum(c.t_espera or 0 for c in started)/len(started) if started else 0
        q = len(state.cola_preferencial)+len(state.cola_general)
        busy = sum(c is not None for c in state.cajeros)
        self.metricas.set(f"LLEGADAS {arrived:4d}   COLA {q:4d}   ATENDIDOS {served:4d}   ESPERA {wait:6.2f} min   OCUPACIÓN {busy/len(state.cajeros):5.0%}")

    def destroy(self): self.cancelar(); super().destroy()


def main() -> int:
    app = AplicacionSimulacion(); app.mainloop(); return 0


if __name__ == "__main__": raise SystemExit(main())
