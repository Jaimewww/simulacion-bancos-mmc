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


def prob_vacio(lam: float, mu: float, c: int) -> float:
    """P0: probability the system is empty (all tellers available)."""
    # TODO(alex-francis-07, issue #3): implementar formula de arriba con math
    raise NotImplementedError


def prob_espera(lam: float, mu: float, c: int) -> float:
    """P(wait) = Erlang C."""
    raise NotImplementedError


def lq(lam: float, mu: float, c: int) -> float:
    """Lq = P(wait)*rho/(1-rho)."""
    raise NotImplementedError


def wq(lam: float, mu: float, c: int) -> float:
    """Wq = Lq/lam."""
    raise NotImplementedError


def l_sistema(lam: float, mu: float, c: int) -> float:
    """L (mean number in system) = Lq + lam/mu."""
    raise NotImplementedError
