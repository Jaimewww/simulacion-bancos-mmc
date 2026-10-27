"""Report figures for the simulation results.

Responsable: Jaime Landazuri (@Jaimewww) — Tarea #4, commit D1.

Spec: compare FCFS vs priority GLOBAL metrics against the analytical
model across teller counts, and per-level waits from the simulation.

Key figures:
  F1. Wq per level (preferential vs general) vs c, priority discipline.
  F2. Wq global (FCFS) vs c, with analytical Erlang C curve overlaid.
  F3. Utilization rho and idle capacity (1-rho) vs c.
Data comes from src/control.experimentos output (CSV in salidas/).
"""

# TODO(jaimewww, issue #4): implementar con matplotlib; salvar en salidas/figuras/
