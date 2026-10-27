"""Shared-teller system state: two logical queues, one teller pool.

Responsable: Fernando Patiño (@Fede-dev11) — Tarea #2, commit B1.

Spec: c identical tellers shared by both levels. If a teller is free,
arriving client starts service. When all are busy, Client waits in the
queue of his level. On release: first preferential; if none, first
general. FCFS inside each level. No teller remains idle while
anyone waits. Unlimited queue and population capacity: no balking,
no rejection.
"""

from .resultados import Disciplina


class Sistema:
    """State of the queueing system at a simulation instant."""

    def __init__(self, c: int, disciplina: Disciplina = Disciplina.PRIORIDAD) -> None:
        self.c = c
        self.disciplina = disciplina
        # TODO(Fede-dev11, issue #2): colas lógicas separadas, FIFO por nivel
        # y pool de cajeros (contador de ocupados + cliente/fin de servicio en curso).
        raise NotImplementedError

    # TODO(fede-dev11, issue #2): operaciones del estado
    # def hay_cajero_libre(self) -> bool: ...
    # def encolar(self, cliente: Cliente) -> None: ...
    # def siguiente_cliente(self) -> Cliente | None:
    #     """Primer preferencial; si no hay, primer general (FCFS por nivel)."""
    # def iniciar_servicio(self, cliente: Cliente, t: float) -> float:
    #     """Asigna cajero; devuelve el instante de fin de servicio."""
    # def finalizar_servicio(self, cliente: Cliente, t: float) -> None: ...
    #
    # Metricas de estado (promedios temporales, no muestreo en llegadas):
    # def longitud_colas(self) -> tuple[int, int]  # (preferencial, general)
    # def utilizacion_instantanea(self) -> float   # ocupados / c
