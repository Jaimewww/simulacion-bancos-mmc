# Vista local Python

Esta interfaz utiliza directamente `ParametrosEscenario`, `MotorDES`,
`ResultadoCorrida` y `reconstruir_tablero`; no contiene un motor JavaScript.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python vista_local.py
```

Permite tasas editables, semilla, disciplina, horizonte y 1–24 cajeros. Las
dos colas y la tabla de cajeros incorporan barras de desplazamiento. El replay
se construye exclusivamente con los eventos producidos por el backend Python.

La pestana **Graficas** muestra la ocupacion real de los cajeros durante la
corrida y compara la carga ofrecida `lambda/mu` con la capacidad instalada.
Tambien presenta rho teorico, utilizacion y ociosidad simuladas.
