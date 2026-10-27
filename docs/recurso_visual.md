# Recurso visual: figuras D1 y tablero D2

**D1 (figuras) está implementado en `src/vista/graficas.py`.** El tablero D2
sigue siendo una propuesta, todavía no implementada.

## D1: figuras del informe (implementadas)

```text
python -m src.vista.graficas <resumen_*.csv> --salida <dir> [--sintetico]
```

Lee el resumen CSV de C2 (no las réplicas) y no simula ni recalcula métricas:
los teóricos vienen de `coherencia_json`. Por familia crea
`d1_<familia>_wq_niveles.png` (Wq preferencial y general por capacidad, FCFS y
prioridad), `d1_<familia>_wq_global_erlang.png` (Wq global y curva Erlang C del
controlador) y `d1_<familia>_utilizacion_ociosidad.png` (ρ y 1-ρ, con los
extremos del IC girados a 1-sup y 1-inf).

Cada figura rotula familia, unidad, p/`origen_p`, réplicas e IC95 % t de
Student. Una métrica vacía queda ausente: no se dibuja como cero y, con n<2,
no se agrega barra de IC. Mezclar unidades dentro de una familia es un error.
`--sintetico` solo rotula "datos sintéticos: no son resultados del estudio",
para que una prueba con datos inventados no se confunda con el estudio. El
backend lo define el entorno (`MPLBACKEND=Agg` en pruebas) y la CLI cierra las
figuras. Son figuras descriptivas: sin τp/τg no eligen capacidad óptima y los
IC entre réplicas no prueban equivalencia con Erlang C.

## D2: tablero de colas y cajeros (propuesta)
 Un dibujo con Matplotlib
que consume una instantánea de eventos de una corrida real del motor.
No requiere servidor web, NetLogo ni un segundo simulador.

```text
Tiempo simulado: 12.5 min        Disciplina: prioridad
Cajeros:       [ocupado] [libre] [ocupado]
Preferencial:  P3 → P4
General:       G8 → G9 → G10
```

El ejemplo solo ilustra la disposición: en una corrida real no debe haber
cajero libre con clientes esperando después de procesar el instante.
Usar etiquetas además de colores para distinguir los niveles.

**Entrega mínima:** imagen con todos los cajeros, las dos colas, reloj,
leyenda y número de clientes esperando. Elegir capturas de una corrida
congestiva para explicar la prioridad; con 8–12 cajeros y la tasa de Adams
puede haber poca espera. No alterar tasas a escondidas para hacerla vistosa.

Al quedar libre un cajero, se destaca el siguiente preferencial o, si no
hay ninguno, el siguiente general. Una atención iniciada nunca se corta.
FCFS usa las mismas etiquetas pero respeta el orden global de llegada.

**Opcional:** controles de siguiente evento/reproducción sobre el registro
existente. No generar nuevas llegadas ni servicios desde la vista. Mostrar
esperas acumuladas como descriptivas de esa corrida, no como estimaciones
estacionarias ni evidencia suficiente del número óptimo.

El tablero explica el mecanismo; las gráficas de espera por nivel, IC y
utilización sustentan las conclusiones. Ninguna animación reemplaza esas
comparaciones. El tablero no tiene comandos de exportación implementados todavía; D1 sí
tiene su CLI.
