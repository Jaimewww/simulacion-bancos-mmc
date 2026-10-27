"""Lightweight contracts to complete in Ivett's A2 contribution."""

from dataclasses import dataclass
from enum import Enum


class Disciplina(Enum):
    FCFS = "fcfs"
    PRIORIDAD = "prioridad"


@dataclass(frozen=True)
class Evento:
    """Replay record; snapshot fields and tie order to be agreed in A2/B1."""

    instante: float
    tipo: str
    cliente_id: int


# A2 contract: run results must carry scenario/seed/units/discipline,
# client records, replay snapshots, time integrals over the measurement
# window, and arrived/completed/pending counts by level. No fabricated data.
