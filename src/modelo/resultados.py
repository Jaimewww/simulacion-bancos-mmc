"""Run-result contracts: disciplines, event log, per-level counts and metrics.

Responsable: Ivett Zaragocin (@ivecanahi) — Tarea #1, commit A2.

A run result carries its scenario (with unit), seed, discipline, client
records, replay events and a metrics container, plus arrived/completed/
pending counts by level derived from the clients. Pending clients are
those still in queue or in service when the run stops. Events at the
same instant keep their log order (tie order is fixed by the engine, B1/B2).
No fabricated data: metrics are filled by C1 from real runs.
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Iterable, Mapping

from .cliente import Cliente, EstadoCliente, Nivel
from .parametros import ParametrosEscenario, Unidad


class Disciplina(Enum):
    FCFS = "fcfs"              # global FCFS reference, levels ignored
    PRIORIDAD = "prioridad"    # non-preemptive priority, FCFS inside each level


class TipoEvento(Enum):
    LLEGADA = "llegada"
    INICIO_SERVICIO = "inicio_servicio"
    FIN_SERVICIO = "fin_servicio"


def _es_entero_no_negativo(valor) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool) and valor >= 0


@dataclass(frozen=True)
class Evento:
    """Replay record; cajero is required for service events, None on arrival."""

    instante: float
    tipo: TipoEvento
    cliente_id: int
    cajero: int | None = None

    def __post_init__(self) -> None:
        valido = isinstance(self.instante, (int, float)) and not isinstance(self.instante, bool)
        if not valido or not math.isfinite(self.instante) or self.instante < 0:
            raise ValueError(f"instante debe ser finito >= 0: {self.instante!r}")
        if not isinstance(self.tipo, TipoEvento):
            raise ValueError(f"tipo debe ser TipoEvento: {self.tipo!r}")
        if not _es_entero_no_negativo(self.cliente_id):
            raise ValueError(f"cliente_id debe ser un entero >= 0: {self.cliente_id!r}")
        if self.tipo is TipoEvento.LLEGADA:
            if self.cajero is not None:
                raise ValueError("una llegada no tiene cajero")
        elif not _es_entero_no_negativo(self.cajero):
            raise ValueError(f"{self.tipo.value} requiere cajero >= 0: {self.cajero!r}")


def validar_registro_eventos(eventos: Iterable[Evento]) -> tuple[Evento, ...]:
    """Returns the log as a tuple; raises ValueError if time ever decreases."""
    registro = tuple(eventos)
    for previo, actual in zip(registro, registro[1:]):
        if actual.instante < previo.instante:
            raise ValueError(
                f"registro desordenado: {actual.instante} después de {previo.instante}"
            )
    return registro


@dataclass(frozen=True)
class ConteoNivel:
    """Clients of one level; invariant atendidos + pendientes == ingresados."""

    ingresados: int
    atendidos: int
    pendientes: int    # still in queue or in service at the end of the run

    def __post_init__(self) -> None:
        if not all(map(_es_entero_no_negativo, (self.ingresados, self.atendidos, self.pendientes))):
            raise ValueError(f"conteos deben ser enteros >= 0: {self}")
        if self.atendidos + self.pendientes != self.ingresados:
            raise ValueError(f"atendidos + pendientes != ingresados: {self}")


def _ids_unicos(clientes: Iterable[Cliente]) -> tuple[Cliente, ...]:
    registro = tuple(clientes)
    ids = [c.id_llegada for c in registro]
    if len(set(ids)) != len(ids):
        raise ValueError("id_llegada repetido: un cliente se cuenta una sola vez")
    return registro


def contar_por_nivel(clientes: Iterable[Cliente]) -> dict[Nivel, ConteoNivel]:
    """Counts each client once in its level; every level is always present."""
    registro = _ids_unicos(clientes)
    conteos = {}
    for nivel in Nivel:
        del_nivel = [c for c in registro if c.nivel is nivel]
        atendidos = sum(c.estado is EstadoCliente.ATENDIDO for c in del_nivel)
        conteos[nivel] = ConteoNivel(len(del_nivel), atendidos, len(del_nivel) - atendidos)
    return conteos


@dataclass(frozen=True)
class ResultadoCorrida:
    """One replication of one scenario under one discipline.

    metricas maps names to numbers or None (not computable, e.g. no client
    served); it is read-only. Times are in parametros.unidad.
    """

    parametros: ParametrosEscenario
    semilla: int
    disciplina: Disciplina
    clientes: tuple[Cliente, ...]
    eventos: tuple[Evento, ...]
    metricas: Mapping[str, float | None] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.parametros, ParametrosEscenario):
            raise TypeError(f"parametros debe ser ParametrosEscenario: {self.parametros!r}")
        if not _es_entero_no_negativo(self.semilla):
            raise ValueError(f"semilla debe ser un entero >= 0: {self.semilla!r}")
        if not isinstance(self.disciplina, Disciplina):
            raise ValueError(f"disciplina debe ser Disciplina: {self.disciplina!r}")
        clientes = _ids_unicos(self.clientes)
        eventos = validar_registro_eventos(self.eventos)
        ids = {c.id_llegada for c in clientes}
        desconocidos = {e.cliente_id for e in eventos} - ids
        if desconocidos:
            raise ValueError(f"eventos de clientes inexistentes: {sorted(desconocidos)}")
        metricas = dict(self.metricas)
        for nombre, valor in metricas.items():
            numero = isinstance(valor, (int, float)) and not isinstance(valor, bool)
            if not isinstance(nombre, str) or not (valor is None or numero):
                raise ValueError(f"métrica inválida: {nombre!r} = {valor!r}")
        object.__setattr__(self, "clientes", clientes)
        object.__setattr__(self, "eventos", eventos)
        object.__setattr__(self, "metricas", MappingProxyType(metricas))

    @property
    def unidad(self) -> Unidad:
        return self.parametros.unidad

    @property
    def conteos(self) -> dict[Nivel, ConteoNivel]:
        """Arrived/completed/pending by level, derived from the client records."""
        return contar_por_nivel(self.clientes)
