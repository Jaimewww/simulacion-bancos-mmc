"""Tablero D2: captura estática de una corrida real (Jaime, tarea #4).

La vista es de solo lectura. `reconstruir_tablero` recorre el registro de
eventos ya producido por `MotorDES` y reconstruye el estado en un instante
dado, procesando los eventos con `instante <= t` en el mismo orden del
registro (B2: primero fines de servicio por cajero, luego llegadas por id).
No simula, no crea eventos ni sortea números: no existe un segundo modelo de
colas aquí. `dibujar_tablero` dibuja esa instantánea inmutable con Matplotlib.

Los `None` del modelo se conservan: un cliente ausente de un cajero es libre,
una cola vacía se rotula como tal y τp/τg quedan como "no definido" cuando el
escenario no los fija. No se agregan condiciones demográficas ni repartos
entre condiciones preferenciales. El backend lo decide el entorno.
"""

import math
import textwrap
from collections.abc import Mapping
from dataclasses import dataclass

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

from ..modelo.cliente import Nivel
from ..modelo.resultados import Disciplina, Evento, ResultadoCorrida, TipoEvento

_COLOR_OCUPADO = "#d62728"
_COLOR_LIBRE = "#2ca02c"
_COLOR_PREFERENCIAL = "#1f77b4"
_COLOR_GENERAL = "#ff7f0e"
_PREFIJO = {Nivel.PREFERENCIAL: "P", Nivel.GENERAL: "G"}


@dataclass(frozen=True)
class EstadoTablero:
    """Instantánea inmutable: cajero -> cliente (o None) y colas en orden."""

    instante: float
    unidad: str
    disciplina: Disciplina
    familia: str
    semilla: int
    p: float
    origen_p: str
    horizonte: float
    cajeros: tuple[int | None, ...]
    cola_preferencial: tuple[int, ...]
    cola_general: tuple[int, ...]
    tau_p: float | None
    tau_g: float | None


def _validar_instante(instante, horizonte: float) -> float:
    valido = isinstance(instante, (int, float)) and not isinstance(instante, bool)
    if not valido or not math.isfinite(instante):
        raise ValueError(f"instante debe ser un número finito: {instante!r}")
    if not 0.0 <= instante <= horizonte:
        raise ValueError(f"instante fuera de [0, {horizonte:g}]: {instante!r}")
    return float(instante)


def _cajero(evento: Evento) -> int:
    if evento.cajero is None:  # Evento ya lo prohíbe; se documenta el contrato.
        raise ValueError(f"registro inconsistente: {evento.tipo.value} sin cajero")
    return evento.cajero


def _quitar(cola: list[int], cliente_id: int, tipo: TipoEvento) -> None:
    try:
        cola.remove(cliente_id)
    except ValueError:
        raise ValueError(
            f"registro inconsistente: {tipo.value} de cliente {cliente_id} que no esperaba"
        ) from None


def reconstruir_tablero(resultado: ResultadoCorrida, instante) -> EstadoTablero:
    """Estado del tablero en `instante` usando solo los eventos registrados."""
    if not isinstance(resultado, ResultadoCorrida):
        raise TypeError(f"resultado debe ser ResultadoCorrida: {resultado!r}")
    horizonte = resultado.parametros.horizon
    instante = _validar_instante(instante, horizonte)

    niveles: Mapping[int, Nivel] = {c.id_llegada: c.nivel for c in resultado.clientes}
    colas: dict[Nivel, list[int]] = {Nivel.PREFERENCIAL: [], Nivel.GENERAL: []}
    ocupados: dict[int, int] = {}
    for evento in resultado.eventos:
        if evento.instante > instante:
            break
        if evento.tipo is TipoEvento.LLEGADA:
            colas[niveles[evento.cliente_id]].append(evento.cliente_id)
        elif evento.tipo is TipoEvento.INICIO_SERVICIO:
            _quitar(colas[niveles[evento.cliente_id]], evento.cliente_id,
                    evento.tipo)
            ocupados[_cajero(evento)] = evento.cliente_id
        elif ocupados.pop(_cajero(evento), None) != evento.cliente_id:
            raise ValueError(
                f"registro inconsistente: {evento.tipo.value} de cliente "
                f"{evento.cliente_id} en cajero {evento.cajero}"
            )

    parametros = resultado.parametros
    return EstadoTablero(
        instante=instante,
        unidad=parametros.unidad.value,
        disciplina=resultado.disciplina,
        familia=parametros.familia or parametros.nombre,
        semilla=resultado.semilla,
        p=parametros.p,
        origen_p=parametros.origen_p,
        horizonte=horizonte,
        cajeros=tuple(ocupados.get(numero) for numero in range(parametros.c)),
        cola_preferencial=tuple(colas[Nivel.PREFERENCIAL]),
        cola_general=tuple(colas[Nivel.GENERAL]),
        tau_p=parametros.tau_p,
        tau_g=parametros.tau_g,
    )


def _tau(valor: float | None) -> str:
    return "no definido" if valor is None else f"{valor:g}"


def _caja(ax, x, y, ancho, alto, texto, color) -> None:
    ax.add_patch(Rectangle((x, y), ancho, alto, facecolor=color, edgecolor=color,
                           alpha=0.18, linewidth=1.2))
    ax.text(x + ancho / 2, y + alto / 2, texto, ha="center", va="center",
            fontsize=8)


def _fila_cola(ax, y, etiqueta, ids, color, prefijo) -> None:
    ax.text(0.02, y, f"{etiqueta} (n={len(ids)})", fontsize=9,
            fontweight="bold", color=color)
    orden = " → ".join(f"{prefijo}{cliente}" for cliente in ids) or "(vacía)"
    ax.text(0.34, y, orden, fontsize=9)


def dibujar_tablero(estado: EstadoTablero):
    """Figura con reloj, cajeros, ambas colas, leyenda y supuestos."""
    if not isinstance(estado, EstadoTablero):
        raise TypeError(f"estado debe ser EstadoTablero: {estado!r}")
    fig = plt.figure(figsize=(9.5, 5.6), layout="constrained")
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    fig.suptitle(f"Tablero D2 — t = {estado.instante:g} {estado.unidad} · "
                 f"horizonte {estado.horizonte:g} {estado.unidad}",
                 fontsize=11, x=0.02, ha="left")
    ax.set_title(
        f"Disciplina: {estado.disciplina.value} · Familia: {estado.familia} · "
        f"semilla: {estado.semilla} · p={estado.p:g} · origen_p: {estado.origen_p}",
        fontsize=8, loc="left")

    cantidad = len(estado.cajeros)
    ax.text(0.02, 0.90, f"Cajeros (c={cantidad}):", fontsize=9,
            fontweight="bold")
    ancho = 0.96 / cantidad
    for numero, cliente in enumerate(estado.cajeros):
        _caja(ax, 0.02 + numero * ancho, 0.72, ancho - 0.01, 0.13,
              f"Cajero {numero}\n" + ("libre" if cliente is None
                                      else f"cliente {cliente}"),
              _COLOR_LIBRE if cliente is None else _COLOR_OCUPADO)

    _fila_cola(ax, 0.52, "Cola preferencial", estado.cola_preferencial,
               _COLOR_PREFERENCIAL, _PREFIJO[Nivel.PREFERENCIAL])
    _fila_cola(ax, 0.36, "Cola general", estado.cola_general,
               _COLOR_GENERAL, _PREFIJO[Nivel.GENERAL])

    ax.legend(handles=[
        Rectangle((0, 0), 1, 1, facecolor=_COLOR_OCUPADO, alpha=0.4,
                  label="ocupado"),
        Rectangle((0, 0), 1, 1, facecolor=_COLOR_LIBRE, alpha=0.4,
                  label="libre"),
        Line2D([], [], color=_COLOR_PREFERENCIAL, marker="s",
               label="esperando preferencial"),
        Line2D([], [], color=_COLOR_GENERAL, marker="s",
               label="esperando general"),
    ], loc="lower center", bbox_to_anchor=(0.5, 0.20), ncol=4, fontsize=8,
        frameon=False)

    ax.text(0.02, 0.04, textwrap.fill(
        "Captura estática de una corrida del MotorDES; no simula, no sortea ni "
        "modifica resultados. Supuestos sin definir no se inventan: "
        f"τp={_tau(estado.tau_p)}, τg={_tau(estado.tau_g)}. Sin τp/τg no se "
        "elige capacidad óptima; el tablero explica el mecanismo, no sustenta "
        "conclusiones.", 118), fontsize=7, va="bottom")
    return fig
