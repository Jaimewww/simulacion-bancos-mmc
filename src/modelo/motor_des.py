"""Motor de simulación de eventos discretos para el sistema M/M/c.

Responsable: Fernando Patiño (@Fede-dev11) — Tarea #2, commit B2.

Las llegadas preferenciales y generales son procesos de Poisson independientes;
los servicios son exponenciales con una tasa común. La carga se genera antes de
aplicar la disciplina, para comparar exactamente las mismas entradas.

No se drena después del horizonte: los clientes en cola o servicio se conservan
como pendientes. Las integrales usan exclusivamente ``[warmup, horizon]``.
En empates se procesan primero los fines por cajero y luego las llegadas por id.
"""

import heapq
import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .cliente import Cliente, Nivel
from .parametros import ParametrosEscenario
from .resultados import Disciplina, Evento, ResultadoCorrida, TipoEvento
from .sistema import Sistema


@dataclass(frozen=True)
class LlegadaPlaneada:
    """Entrada aleatoria preasignada e independiente de la disciplina."""

    id_llegada: int
    instante: float
    nivel: Nivel
    duracion_servicio: float

    def __post_init__(self) -> None:
        if not isinstance(self.id_llegada, int) or isinstance(self.id_llegada, bool):
            raise ValueError("id_llegada debe ser un entero")
        if self.id_llegada < 0:
            raise ValueError("id_llegada debe ser >= 0")
        if not isinstance(self.nivel, Nivel):
            raise ValueError("nivel debe ser Nivel")
        for nombre in ("instante", "duracion_servicio"):
            valor = getattr(self, nombre)
            if (not isinstance(valor, (int, float)) or isinstance(valor, bool)
                    or not math.isfinite(valor) or valor < 0):
                raise ValueError(f"{nombre} debe ser finito y >= 0")
        if self.duracion_servicio == 0:
            raise ValueError("duracion_servicio debe ser > 0")


def _instantes_poisson(
    rng: np.random.Generator, tasa: float, horizonte: float
) -> list[float]:
    if tasa == 0:
        return []
    instantes: list[float] = []
    instante = float(rng.exponential(1.0 / tasa))
    while instante <= horizonte:
        instantes.append(instante)
        instante += float(rng.exponential(1.0 / tasa))
    return instantes


def generar_carga(
    parametros: ParametrosEscenario, semilla: int
) -> tuple[LlegadaPlaneada, ...]:
    """Genera llegadas y servicios reproducibles para ambas disciplinas."""
    if not isinstance(parametros, ParametrosEscenario):
        raise TypeError("parametros debe ser ParametrosEscenario")
    if not isinstance(semilla, int) or isinstance(semilla, bool) or semilla < 0:
        raise ValueError("semilla debe ser un entero >= 0")
    rng = np.random.default_rng(semilla)
    llegadas = [
        *((t, Nivel.PREFERENCIAL) for t in _instantes_poisson(
            rng, parametros.lam_p, parametros.horizon
        )),
        *((t, Nivel.GENERAL) for t in _instantes_poisson(
            rng, parametros.lam_g, parametros.horizon
        )),
    ]
    llegadas.sort(key=lambda item: (item[0], item[1]))
    return tuple(
        LlegadaPlaneada(
            id_llegada=numero,
            instante=instante,
            nivel=nivel,
            duracion_servicio=float(rng.exponential(1.0 / parametros.mu)),
        )
        for numero, (instante, nivel) in enumerate(llegadas)
    )


class MotorDES:
    """Ejecuta una réplica y devuelve clientes, eventos y métricas temporales."""

    def __init__(
        self,
        parametros: ParametrosEscenario,
        disciplina: Disciplina = Disciplina.PRIORIDAD,
        *,
        semilla: int | None = None,
        carga: Iterable[LlegadaPlaneada] | None = None,
    ) -> None:
        if not isinstance(parametros, ParametrosEscenario):
            raise TypeError("parametros debe ser ParametrosEscenario")
        if not isinstance(disciplina, Disciplina):
            raise ValueError("disciplina debe ser Disciplina")
        semilla_efectiva = parametros.seed if semilla is None else semilla
        if (not isinstance(semilla_efectiva, int) or isinstance(semilla_efectiva, bool)
                or semilla_efectiva < 0):
            raise ValueError("se requiere una semilla entera >= 0")
        self.parametros = parametros
        self.disciplina = disciplina
        self.semilla = semilla_efectiva
        self.carga = generar_carga(parametros, self.semilla) if carga is None else tuple(carga)
        self._validar_carga()

    def _validar_carga(self) -> None:
        if not all(isinstance(item, LlegadaPlaneada) for item in self.carga):
            raise TypeError("carga contiene una llegada no válida")
        ids = [item.id_llegada for item in self.carga]
        if len(ids) != len(set(ids)):
            raise ValueError("carga contiene ids repetidos")
        claves = [(item.instante, item.id_llegada) for item in self.carga]
        if claves != sorted(claves):
            raise ValueError("carga debe estar ordenada por instante e id")
        if any(item.instante > self.parametros.horizon for item in self.carga):
            raise ValueError("carga contiene llegadas posteriores al horizonte")

    @staticmethod
    def _acumular(
        desde: float,
        hasta: float,
        sistema: Sistema,
        warmup: float,
        horizon: float,
        areas: dict[str, float],
    ) -> None:
        inicio = max(desde, warmup)
        fin = min(hasta, horizon)
        if fin <= inicio:
            return
        duracion = fin - inicio
        preferenciales, generales = sistema.longitud_colas()
        areas["cola_preferencial"] += duracion * preferenciales
        areas["cola_general"] += duracion * generales
        areas["ocupados"] += duracion * sistema.cantidad_ocupados

    def correr(self) -> ResultadoCorrida:
        """Ejecuta hasta ``horizon`` sin drenaje y devuelve la réplica."""
        sistema = Sistema(self.parametros.c, self.disciplina)
        clientes: list[Cliente] = []
        eventos: list[Evento] = []
        duraciones = {item.id_llegada: item.duracion_servicio for item in self.carga}
        calendario: list[tuple[float, int, int, int, str, Cliente]] = []
        secuencia = 0
        for item in self.carga:
            actual = Cliente(item.id_llegada, item.nivel, item.instante)
            clientes.append(actual)
            heapq.heappush(
                calendario,
                (item.instante, 1, item.id_llegada, secuencia, "llegada", actual),
            )
            secuencia += 1

        areas = {"cola_preferencial": 0.0, "cola_general": 0.0, "ocupados": 0.0}
        instante_anterior = 0.0
        while calendario and calendario[0][0] <= self.parametros.horizon:
            instante, _, _, _, tipo, actual = heapq.heappop(calendario)
            self._acumular(
                instante_anterior, instante, sistema,
                self.parametros.warmup, self.parametros.horizon, areas,
            )
            instante_anterior = instante
            if tipo == "llegada":
                eventos.append(Evento(instante, TipoEvento.LLEGADA, actual.id_llegada))
                cajero = sistema.recibir(actual, instante)
                if cajero is not None:
                    eventos.append(Evento(
                        instante, TipoEvento.INICIO_SERVICIO, actual.id_llegada, cajero
                    ))
                    fin = instante + duraciones[actual.id_llegada]
                    heapq.heappush(calendario, (fin, 0, cajero, secuencia, "fin", actual))
                    secuencia += 1
                continue

            cajero = actual.cajero
            eventos.append(Evento(instante, TipoEvento.FIN_SERVICIO, actual.id_llegada, cajero))
            siguiente = sistema.finalizar_servicio(actual, instante)
            if siguiente is not None:
                eventos.append(Evento(
                    instante, TipoEvento.INICIO_SERVICIO, siguiente.id_llegada, cajero
                ))
                fin = instante + duraciones[siguiente.id_llegada]
                heapq.heappush(calendario, (fin, 0, cajero, secuencia, "fin", siguiente))
                secuencia += 1

        self._acumular(
            instante_anterior, self.parametros.horizon, sistema,
            self.parametros.warmup, self.parametros.horizon, areas,
        )
        ventana = self.parametros.horizon - self.parametros.warmup
        metricas = {
            "inicio_medicion": self.parametros.warmup,
            "fin_medicion": self.parametros.horizon,
            "ventana_medida": ventana,
            "area_cola_preferencial": areas["cola_preferencial"],
            "area_cola_general": areas["cola_general"],
            "area_ocupados": areas["ocupados"],
            "lq_preferencial": areas["cola_preferencial"] / ventana,
            "lq_general": areas["cola_general"] / ventana,
            "lq_global": (areas["cola_preferencial"] + areas["cola_general"]) / ventana,
            "utilizacion": areas["ocupados"] / (self.parametros.c * ventana),
        }
        return ResultadoCorrida(
            parametros=self.parametros,
            semilla=self.semilla,
            disciplina=self.disciplina,
            clientes=tuple(clientes),
            eventos=tuple(eventos),
            metricas=metricas,
        )
