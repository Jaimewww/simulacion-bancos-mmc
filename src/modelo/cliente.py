"""Client entity and priority level of the banking queue.

Responsable: Ivett Zaragocin (@ivecanahi) — Tarea #1, commit A1.

Spec: priority level k = 1 groups elderly adults, people with
disabilities and pregnant women at ONE same level, without
hierarchies between them. A person meeting several conditions is
counted once. FCFS is kept inside each level (arrival id breaks ties).
Non-preemptive priority: an ongoing service is never interrupted.
"""

from dataclasses import dataclass
from enum import IntEnum


class Nivel(IntEnum):
    PREFERENCIAL = 1
    GENERAL = 2


@dataclass
class Cliente:
    """One arriving client with its simulation timestamps."""

    id_llegada: int = 0        # sequence number; ties inside a level resolve FCFS
    nivel: Nivel = Nivel.GENERAL
    t_llegada: float = 0.0
    t_inicio_servicio: float | None = None
    t_fin_servicio: float | None = None

    # TODO(ivecanahi, issue #1): propiedad referenciales de conveniencia
    # - t_espera: espera hasta iniciar servicio (None si no inició)
    # - t_sistema: tiempo total en sistema (None si no terminó)
