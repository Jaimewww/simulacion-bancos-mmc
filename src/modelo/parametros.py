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
"""

from dataclasses import dataclass


@dataclass
class ParametrosEscenario:
    """Input parameters of one simulated scenario."""

    nombre: str = ""          # scenario family name, e.g. "adams|c=10"
    lam: float = 0.0          # total arrival rate (clients / time unit)
    lam_p: float = 0.0        # preferential arrival rate
    lam_g: float = 0.0        # general arrival rate; lam = lam_p + lam_g
    mu: float = 0.0           # common service rate per teller
    c: int = 1                # number of shared tellers
    p: float | None = None    # preferential proportion (assumption, documented)
    horizon: float = 0.0      # simulation horizon in time units
    warmup: float = 0.0       # warm-up discarded from statistics
    tau_p: float | None = None   # acceptable-wait criterion, level 1 (pending source)
    tau_g: float | None = None   # acceptable-wait criterion, level 2 (pending source)
    seed: int | None = None   # recorded seed for reproducibility


def familia_adams_yeboah(c: int, p: float, seed: int | None = None) -> ParametrosEscenario:
    """Family [1]: lam = 45/h, mu = 12/h/teller (service mean 5 min)."""
    # TODO(ivecanahi, issue #1): implementar y validar a = lam/mu = 3.75 erlangs
    raise NotImplementedError


def familia_marhamah(c: int, p: float, seed: int | None = None) -> ParametrosEscenario:
    """Family [2]: lam = 0.3246/min, mu = 0.2839/min."""
    # TODO(ivecanahi, issue #1): validar estabilidad rho < 1 por familia
    raise NotImplementedError
