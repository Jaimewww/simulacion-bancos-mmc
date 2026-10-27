"""Analytical M/M/c model (Erlang C) for global-metric contrast.

Responsable: Alex Sigcho (@Alex-Francis-07) — Tarea #3, commit C1.

Spec: stationary expressions describe the WHOLE system only, not each
level (lam = lam_p + lam_g; service rate min(n, c)*mu in state n).
Requires rho = lam / (c*mu) < 1.
  P0 = [sum(n=0..c-1) a^n/n! + a^c/(c!*(1-rho))]^-1,   a = lam/mu
  P(wait) = a^c * P0 / (c! * (1-rho))
  Lq = P(wait) * rho / (1-rho)
  L  = Lq + lam/mu = Lq + a
  Wq = Lq / lam ;  W = Wq + 1/mu

Level split uses Little's law only as consistency check of the
simulation: Lq_p = lam_p*Wq_p; Lq_g = lam_g*Wq_g; Lq = Lq_p + Lq_g;
Wq = (lam_p*Wq_p + lam_g*Wq_g)/lam. The global Wq is never assigned
to both levels and no two independent M/M/c systems are computed.
"""

import math

from .parametros import ParametrosEscenario


def _validar_mm_c(lam: float, mu: float, c: int) -> tuple[float, float, float]:
    if not isinstance(c, int) or isinstance(c, bool) or c <= 0:
        raise ValueError(f"c debe ser un entero positivo: {c!r}")
    for nombre, valor in (("lam", lam), ("mu", mu)):
        if not isinstance(valor, (int, float)) or isinstance(valor, bool) or not math.isfinite(valor) or valor <= 0:
            raise ValueError(f"{nombre} debe ser un número finito > 0: {valor!r}")
    rho = lam / (c * mu)
    if rho >= 1.0 - 1e-18:
        raise ValueError(f"rho >= 1, sin régimen estacionario para contraste analítico: rho={rho}")
    a = lam / mu
    return a, rho, lam


def prob_vacio(lam: float, mu: float, c: int) -> float:
    """P0: probability the system is empty (all tellers available)."""
    a, rho, _ = _validar_mm_c(lam, mu, c)
    suma = 0.0
    for n in range(c):
        suma += (a ** n) / math.factorial(n)
    suma += (a ** c) / (math.factorial(c) * (1.0 - rho))
    if suma <= 0:
        raise ValueError("P0 no calculable")
    return 1.0 / suma


def prob_espera(lam: float, mu: float, c: int) -> float:
    """P(wait) = Erlang C."""
    a, rho, _ = _validar_mm_c(lam, mu, c)
    p0 = prob_vacio(lam, mu, c)
    return (a ** c) * p0 / (math.factorial(c) * (1.0 - rho))


def lq(lam: float, mu: float, c: int) -> float:
    """Lq = P(wait)*rho/(1-rho)."""
    _, rho, _ = _validar_mm_c(lam, mu, c)
    pw = prob_espera(lam, mu, c)
    return pw * rho / (1.0 - rho)


def wq(lam: float, mu: float, c: int) -> float:
    """Wq = Lq/lam."""
    _, _, lamv = _validar_mm_c(lam, mu, c)
    lqv = lq(lam, mu, c)
    return lqv / lamv


def w_sistema(lam: float, mu: float, c: int) -> float:
    """W = Wq + 1/mu."""
    _, _, _ = _validar_mm_c(lam, mu, c)
    return wq(lam, mu, c) + 1.0 / mu


def l_sistema(lam: float, mu: float, c: int) -> float:
    """L (mean number in system) = Lq + lam/mu."""
    a, _, _ = _validar_mm_c(lam, mu, c)
    return lq(lam, mu, c) + a


def erlang_c_desde_parametros(parametros: ParametrosEscenario) -> dict[str, float]:
    """Erlang C global using scenario totals (lam, mu, c)."""
    if not isinstance(parametros, ParametrosEscenario):
        raise TypeError("parametros debe ser ParametrosEscenario")
    parametros.exigir_estabilidad()
    a = parametros.carga_ofrecida
    rho = parametros.rho
    p0 = prob_vacio(parametros.lam, parametros.mu, parametros.c)
    pw = prob_espera(parametros.lam, parametros.mu, parametros.c)
    lqv = lq(parametros.lam, parametros.mu, parametros.c)
    wqv = wq(parametros.lam, parametros.mu, parametros.c)
    lv = l_sistema(parametros.lam, parametros.mu, parametros.c)
    wv = w_sistema(parametros.lam, parametros.mu, parametros.c)
    return {
        "a": a,
        "rho": rho,
        "p0": p0,
        "P_espera": pw,
        "Lq": lqv,
        "L": lv,
        "Wq": wqv,
        "W": wv,
    }
