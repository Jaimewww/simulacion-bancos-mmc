"""Parameters of the M/M/c model with non-preemptive priority.

Responsable: Ivett Zaragocin (@ivecanahi) — Tarea #1, commit A1.

This module defines the input parameters of each scenario family:
lambdas (arrival rates per level), mu (common service rate),
number of tellers (c), priority proportion p, and simulation horizon.

Spec: two documented families must be supported:
  - Adams & Yeboah: lam = 45/h, mu = 12/h/teller, c in {8..12}
  - Marhamah et al.: lam = 0.3246/min, mu = 0.2839/min, c in {2..5}
Total arrival rate decomposes as lam = lam_p + lam_g (p = lam_p/lam).
Preferential proportion p is an explicit experimental assumption,
never presented as measured data (see SI doc, pending data note).

Every scenario keeps the unit of its family. Rates and times are only
changed through ``en_unidad`` / ``convertir_*``, never mixed silently.
No default exists for p, horizon, warm-up, replicas or tau_p/tau_g:
the caller supplies them and records where p (and tau, if any) come from.
"""

import math
from dataclasses import dataclass, field, replace
from enum import Enum

_TOLERANCIA = 1e-9


class Unidad(Enum):
    """Time unit of a scenario; rates are clients per this unit."""

    HORA = "hora"
    MINUTO = "minuto"


_MINUTOS = {Unidad.HORA: 60.0, Unidad.MINUTO: 1.0}


def convertir_tiempo(valor: float, desde: Unidad, hacia: Unidad) -> float:
    """Converts a duration, e.g. 2 h -> 120 min."""
    return valor * _MINUTOS[desde] / _MINUTOS[hacia]


def convertir_tasa(valor: float, desde: Unidad, hacia: Unidad) -> float:
    """Converts a rate (events per unit), e.g. 45/h -> 0.75/min."""
    return valor * _MINUTOS[hacia] / _MINUTOS[desde]


def _es_real(valor) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def _es_entero(valor) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


def _exigir_positivo(nombre: str, valor) -> None:
    if not _es_real(valor) or not math.isfinite(valor) or valor <= 0:
        raise ValueError(f"{nombre} debe ser un número finito > 0: {valor!r}")


def _exigir_texto(nombre: str, valor) -> None:
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(f"{nombre} debe ser un texto no vacío: {valor!r}")


def _validar_p(p) -> None:
    if not _es_real(p) or not 0.0 <= p <= 1.0:  # NaN fails the comparison
        raise ValueError(f"p debe ser un número en [0, 1]: {p!r}")


def descomponer_llegadas(lam: float, p: float) -> tuple[float, float]:
    """Returns (lam_p, lam_g) = (p*lam, (1-p)*lam), checking lam_p+lam_g = lam."""
    _exigir_positivo("lam", lam)
    _validar_p(p)
    lam_p, lam_g = p * lam, (1.0 - p) * lam
    if not math.isclose(lam_p + lam_g, lam, rel_tol=_TOLERANCIA, abs_tol=_TOLERANCIA):
        raise ArithmeticError(f"lam_p + lam_g != lam ({lam_p} + {lam_g} != {lam})")
    return lam_p, lam_g


@dataclass(frozen=True)
class FamiliaEscenario:
    """Documented rates of a source; values are as cited by the course document."""

    nombre: str
    fuente: str
    lam: float
    mu: float
    unidad: Unidad
    capacidades: tuple[int, ...]


ADAMS_YEBOAH = FamiliaEscenario(
    nombre="adams_yeboah", fuente="Adams & Yeboah",
    lam=45.0, mu=12.0, unidad=Unidad.HORA, capacidades=(8, 9, 10, 11, 12),
)
MARHAMAH = FamiliaEscenario(
    nombre="marhamah", fuente="Marhamah et al.",
    lam=0.3246, mu=0.2839, unidad=Unidad.MINUTO, capacidades=(2, 3, 4, 5),
)


@dataclass(frozen=True, kw_only=True)
class ParametrosEscenario:
    """Validated input parameters of one simulated scenario (immutable)."""

    nombre: str               # scenario id, e.g. "marhamah|c=3"
    unidad: Unidad            # time unit of rates, horizon, warm-up and tau
    lam: float                # total arrival rate (clients / unit)
    mu: float                 # common service rate per teller
    c: int                    # number of shared tellers
    p: float                  # preferential proportion, 0 <= p <= 1
    origen_p: str             # source of p or declared experimental assumption
    horizon: float            # end of the arrival window (same unit)
    warmup: float             # warm-up discarded from statistics, < horizon
    replicas: int | None = None  # experimental decision, None = not fixed yet
    seed: int | None = None   # recorded base seed for reproducibility
    tau_p: float | None = None   # acceptable wait, level 1: pending if None
    tau_g: float | None = None   # acceptable wait, level 2: pending if None
    origen_tau: str | None = None  # required once any tau is given
    familia: str | None = None   # FamiliaEscenario.nombre if documented
    lam_p: float = field(init=False)  # preferential arrival rate = p*lam
    lam_g: float = field(init=False)  # general arrival rate = (1-p)*lam

    def __post_init__(self) -> None:
        _exigir_texto("nombre", self.nombre)
        if not isinstance(self.unidad, Unidad):
            raise TypeError(f"unidad debe ser Unidad: {self.unidad!r}")
        _exigir_positivo("lam", self.lam)
        _exigir_positivo("mu", self.mu)
        if not _es_entero(self.c) or self.c <= 0:
            raise ValueError(f"c debe ser un entero positivo: {self.c!r}")
        _validar_p(self.p)
        _exigir_texto("origen_p", self.origen_p)
        _exigir_positivo("horizon", self.horizon)
        if not _es_real(self.warmup) or not 0.0 <= self.warmup < self.horizon:
            raise ValueError(
                f"se requiere 0 <= warmup < horizon: {self.warmup!r}, {self.horizon!r}"
            )
        if self.replicas is not None and (not _es_entero(self.replicas) or self.replicas <= 0):
            raise ValueError(f"replicas debe ser un entero positivo: {self.replicas!r}")
        if self.seed is not None and (not _es_entero(self.seed) or self.seed < 0):
            raise ValueError(f"seed debe ser un entero >= 0: {self.seed!r}")
        for nombre in ("tau_p", "tau_g"):
            valor = getattr(self, nombre)
            if valor is not None:
                _exigir_positivo(nombre, valor)
                _exigir_texto("origen_tau", self.origen_tau)
        lam_p, lam_g = descomponer_llegadas(self.lam, self.p)
        object.__setattr__(self, "lam_p", lam_p)
        object.__setattr__(self, "lam_g", lam_g)

    @property
    def carga_ofrecida(self) -> float:
        """a = lam/mu, in erlangs."""
        return self.lam / self.mu

    @property
    def rho(self) -> float:
        """Utilization rho = lam / (c*mu)."""
        return self.lam / (self.c * self.mu)

    @property
    def es_estable(self) -> bool:
        """True when rho < 1 (stationary M/M/c contrast is meaningful)."""
        return self.rho < 1.0

    def exigir_estabilidad(self) -> None:
        """Raises ValueError if rho >= 1; call before any Erlang C contrast."""
        if not self.es_estable:
            raise ValueError(f"{self.nombre}: rho = {self.rho:.4f} >= 1, sin régimen estacionario")

    @property
    def criterios_espera_definidos(self) -> bool:
        """True only when both tau_p and tau_g were supplied with an origin."""
        return self.tau_p is not None and self.tau_g is not None

    def en_unidad(self, unidad: Unidad) -> "ParametrosEscenario":
        """Explicit copy with rates and times expressed in another unit."""
        def tiempo(valor):
            return None if valor is None else convertir_tiempo(valor, self.unidad, unidad)

        return replace(
            self,
            unidad=unidad,
            lam=convertir_tasa(self.lam, self.unidad, unidad),
            mu=convertir_tasa(self.mu, self.unidad, unidad),
            horizon=tiempo(self.horizon),
            warmup=tiempo(self.warmup),
            tau_p=tiempo(self.tau_p),
            tau_g=tiempo(self.tau_g),
        )


def crear_escenario(familia: FamiliaEscenario, c: int, p: float, *, origen_p: str,
                    horizon: float, warmup: float, **opcionales) -> ParametrosEscenario:
    """Scenario of a documented family; c must be in its documented range.

    ``opcionales`` accepts replicas, seed, tau_p, tau_g and origen_tau.
    """
    if not _es_entero(c) or c not in familia.capacidades:
        raise ValueError(f"{familia.nombre}: c={c!r} fuera de {familia.capacidades}")
    return ParametrosEscenario(
        nombre=f"{familia.nombre}|c={c}", familia=familia.nombre,
        unidad=familia.unidad, lam=familia.lam, mu=familia.mu, c=c, p=p,
        origen_p=origen_p, horizon=horizon, warmup=warmup, **opcionales,
    )


def escenarios_familia(familia: FamiliaEscenario, **kwargs) -> list[ParametrosEscenario]:
    """One scenario per documented capacity of the family (same p, horizon...)."""
    return [crear_escenario(familia, c, **kwargs) for c in familia.capacidades]


def familia_adams_yeboah(c: int, p: float, **kwargs) -> ParametrosEscenario:
    """Family [1]: lam = 45/h, mu = 12/h/teller (service mean 5 min), hours."""
    return crear_escenario(ADAMS_YEBOAH, c, p, **kwargs)


def familia_marhamah(c: int, p: float, **kwargs) -> ParametrosEscenario:
    """Family [2]: lam = 0.3246/min, mu = 0.2839/min/teller, minutes."""
    return crear_escenario(MARHAMAH, c, p, **kwargs)
