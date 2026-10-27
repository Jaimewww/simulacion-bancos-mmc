"""Scenario experiment matrix and run aggregation.

Responsable: Alex Sigcho (@Alex-Francis-07) — Tarea #3, commit C2.

Spec: for each family (Adams & Yeboah c in {8..12}; Marhamah c in
{2..5}) compare FCFS (baseline) vs non-preemptive priority under the
same total rates and teller count. Each configuration runs several
replications with recorded seeds; warm-up is discarded and pending
(incomplete) clients are reported to avoid truncation bias. Global
metrics are contrasted against the analytical M/M/c; per-level
metrics are checked against Little's law and conservation identities.
"""

# TODO(alex-francis-07, issue #3):
# def ejecutar_escenario(parametros, disciplinas=("fcfs", "prioridad"), repeticiones=30):
#     """Runs all replications for one (family, c) configuration."""
#     # para cada replica: semilla determinista, corre MotorDES, agrega metricas
#     # descarta warmup, cuantifica clientes pendientes, computa media y IC 95%
#
# def agregar_replicas(runs) -> dict:
#     """Mean + 95% CI of Wq per level, Lq (time-weighted), utilization."""
#
# def validar_coherencia(medidas_sim, lam, mu, c) -> list[str]:
#     """Checks: global Wq/Lq vs Erlang C; Little per level; conservation."""
