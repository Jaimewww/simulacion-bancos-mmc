"""Client entity and priority level of the banking queue.

Responsable: Ivett Zaragocin (@ivecanahi) — Tarea #1, commit A2.

Spec: priority level k = 1 groups elderly adults, people with
disabilities and pregnant women at ONE same level, without
hierarchies between them. A person meeting several conditions is
counted once. FCFS is kept inside each level (arrival id breaks ties).
Non-preemptive priority: an ongoing service is never interrupted.

Timestamps follow t_llegada <= t_inicio_servicio <= t_fin_servicio.
A client still waiting or in service at the end of a run is a valid
incomplete record: its missing durations are None, never 0.
Change state through iniciar_servicio/finalizar_servicio, which validate
the order; direct field assignment bypasses those checks.
"""

import math
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Iterable


class Nivel(IntEnum):
    PREFERENCIAL = 1
    GENERAL = 2


class CondicionPreferencial(Enum):
    """Optional label; all conditions share Nivel.PREFERENCIAL (no shares assumed)."""

    ADULTO_MAYOR = "adulto_mayor"
    DISCAPACIDAD = "discapacidad"
    EMBARAZO = "embarazo"


class EstadoCliente(Enum):
    EN_COLA = "en_cola"
    EN_SERVICIO = "en_servicio"
    ATENDIDO = "atendido"


def nivel_por_condiciones(condiciones: Iterable[CondicionPreferencial]) -> Nivel:
    """PREFERENCIAL if any condition applies (however many), else GENERAL."""
    return Nivel.PREFERENCIAL if frozenset(condiciones) else Nivel.GENERAL


def _es_entero_no_negativo(valor) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool) and valor >= 0


def _validar_instante(nombre: str, valor) -> None:
    valido = isinstance(valor, (int, float)) and not isinstance(valor, bool)
    if not valido or not math.isfinite(valor) or valor < 0:
        raise ValueError(f"{nombre} debe ser un instante finito >= 0: {valor!r}")


@dataclass
class Cliente:
    """One arriving client with its simulation timestamps."""

    id_llegada: int            # unique sequence number; ties inside a level resolve FCFS
    nivel: Nivel
    t_llegada: float
    t_inicio_servicio: float | None = None
    t_fin_servicio: float | None = None
    cajero: int | None = None  # teller index, set together with t_inicio_servicio
    condiciones: frozenset[CondicionPreferencial] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        self.condiciones = frozenset(self.condiciones)
        self.validar()

    @classmethod
    def desde_condiciones(cls, id_llegada: int, t_llegada: float,
                          condiciones: Iterable[CondicionPreferencial]) -> "Cliente":
        """Builds a client whose level follows its conditions (deduplicated)."""
        condiciones = frozenset(condiciones)
        return cls(id_llegada=id_llegada, nivel=nivel_por_condiciones(condiciones),
                   t_llegada=t_llegada, condiciones=condiciones)

    def validar(self) -> None:
        """Raises ValueError if identity, level or timestamp order is invalid."""
        if not _es_entero_no_negativo(self.id_llegada):
            raise ValueError(f"id_llegada debe ser un entero >= 0: {self.id_llegada!r}")
        if not isinstance(self.nivel, Nivel):
            raise ValueError(f"nivel debe ser Nivel: {self.nivel!r}")
        if not all(isinstance(c, CondicionPreferencial) for c in self.condiciones):
            raise ValueError(f"condición desconocida: {set(self.condiciones)!r}")
        if self.condiciones and self.nivel is not Nivel.PREFERENCIAL:
            raise ValueError("un cliente con condiciones preferenciales no es GENERAL")
        _validar_instante("t_llegada", self.t_llegada)
        if self.t_inicio_servicio is None:
            if self.t_fin_servicio is not None or self.cajero is not None:
                raise ValueError("fin de servicio o cajero sin inicio de servicio")
            return
        _validar_instante("t_inicio_servicio", self.t_inicio_servicio)
        if self.t_inicio_servicio < self.t_llegada:
            raise ValueError("t_inicio_servicio anterior a t_llegada")
        if not _es_entero_no_negativo(self.cajero):
            raise ValueError(f"cajero debe ser un entero >= 0: {self.cajero!r}")
        if self.t_fin_servicio is not None:
            _validar_instante("t_fin_servicio", self.t_fin_servicio)
            if self.t_fin_servicio < self.t_inicio_servicio:
                raise ValueError("t_fin_servicio anterior a t_inicio_servicio")

    def iniciar_servicio(self, t: float, cajero: int) -> None:
        """Moves EN_COLA -> EN_SERVICIO; state is unchanged on error."""
        if self.estado is not EstadoCliente.EN_COLA:
            raise ValueError(f"cliente {self.id_llegada} no está en cola")
        anterior = (self.t_inicio_servicio, self.cajero)
        self.t_inicio_servicio, self.cajero = t, cajero
        try:
            self.validar()
        except ValueError:
            self.t_inicio_servicio, self.cajero = anterior
            raise

    def finalizar_servicio(self, t: float) -> None:
        """Moves EN_SERVICIO -> ATENDIDO; state is unchanged on error."""
        if self.estado is not EstadoCliente.EN_SERVICIO:
            raise ValueError(f"cliente {self.id_llegada} no está en servicio")
        self.t_fin_servicio = t
        try:
            self.validar()
        except ValueError:
            self.t_fin_servicio = None
            raise

    @property
    def estado(self) -> EstadoCliente:
        if self.t_inicio_servicio is None:
            return EstadoCliente.EN_COLA
        if self.t_fin_servicio is None:
            return EstadoCliente.EN_SERVICIO
        return EstadoCliente.ATENDIDO

    @property
    def t_espera(self) -> float | None:
        """Wait until service start; None while still in queue."""
        if self.t_inicio_servicio is None:
            return None
        return self.t_inicio_servicio - self.t_llegada

    @property
    def t_servicio(self) -> float | None:
        """Service duration; None until service ends."""
        if self.t_fin_servicio is None:
            return None
        return self.t_fin_servicio - self.t_inicio_servicio

    @property
    def t_sistema(self) -> float | None:
        """Total time in system; None until service ends."""
        if self.t_fin_servicio is None:
            return None
        return self.t_fin_servicio - self.t_llegada
