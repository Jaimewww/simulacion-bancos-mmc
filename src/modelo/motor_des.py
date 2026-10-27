"""Discrete-event simulation engine (event calendar).

Responsable: Fernando Patiño (@Fede-dev11) — Tarea #2, commit B2.

Spec: stochastic DES of the M/M/c model with non-preemptive priority.
Poisson arrivals, independent per level, with constant rates lam_p and
lam_g. i.i.d. exponential service times with common rate mu for both
levels (no slower attention assumed by age/disability/pregnancy).
Non-preemptive discipline: service in course is never interrupted;
a preferential arrival takes precedence only when a teller becomes
free. Events: arrival per level, end of service.
"""

class MotorDES:
    """Pending engine: will return client records, replay and time integrals."""

    def __init__(self, parametros) -> None:  # src.modelo.parametros.ParametrosEscenario
        # TODO(fede-dev11, issue #2): calendario de eventos (heapq), RNG con semilla
        # registrada (numpy.random.default_rng(seed)) y motor principal:
        #   1. extraer el próximo evento
        #   2. actualizar métricas temporales integradas (Lq, utilización)
        #   3. aplicar la transición (llegada / fin de servicio)
        #   4. repetir hasta agotar el horizonte
        raise NotImplementedError

    def correr(self) -> list:
        """Returns the list of Cliente with timestamps filled for one run."""
        # TODO(fede-dev11): devolver registros por cliente para la capa control
        raise NotImplementedError
