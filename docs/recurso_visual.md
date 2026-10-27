# Recurso visual: figuras D1 y tablero D2

**D1 (figuras) está implementado en `src/vista/graficas.py`.** **D2 (tablero)
está implementado en `src/vista/animacion.py` con su CLI en
`src/control/tablero.py`.** La entrega es la captura estática mínima; el
replay interactivo opcional no se implementó.

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

## D2: tablero de colas y cajeros (implementado)

La vista reconstruye una instantánea desde el registro de eventos de una
corrida real del `MotorDES` y la dibuja con Matplotlib. No requiere servidor
web, NetLogo ni un segundo simulador: la atención la decide el motor, no la
vista.

```text
Tablero D2 — t = 34.9448 minuto · horizonte 480 minuto
Disciplina: prioridad · Familia: marhamah · semilla: 7 · p=0.3 · origen_p: ...
Cajeros (c=2): [Cajero 0: cliente 10] [Cajero 1: cliente 11]
Cola preferencial (n=1): P13
Cola general (n=1): G12
```

```powershell
.venv/Scripts/python.exe -m src.control.tablero --familia marhamah --c 3 --p 0.3 --origen-p "supuesto de sensibilidad, no medicion" --horizon 480 --warmup 60 --semilla 12345 --instante 300 --salida salidas/tablero/tablero.png
```

`--p`, `--origen-p`, `--horizon` y `--warmup` son obligatorios. El resto de
banderas tiene valores documentados en `--help`; `--instante` omitido usa el
horizonte y el rótulo lo aclara. La CLI valida el escenario y el instante con
el modelo antes de escribir: una entrada inválida termina con código 2 y sin
PNG. La figura se guarda en la ruta de `--salida`.

**Entrega mínima implementada:** todos los cajeros con etiqueta y estado
(`libre` o `cliente N`), las dos colas en orden de atención con etiquetas P/G
y conteos, reloj con unidad, disciplina, familia, semilla, p/`origen_p`,
leyenda de estados y nota de supuestos. Un `None` se conserva: cajero libre,
cola `(vacía)` y `τp`/`τg` como "no definido"; no se agregan condiciones
demográficas ni repartos entre condiciones. Elegir capturas de una corrida
congestiva para explicar la prioridad; con 8–12 cajeros y la tasa de Adams
puede haber poca espera y no se alteran tasas para hacerla vistosa.

La reconstrucción procesa los eventos con `instante <= t` en el orden del
registro B2: primero fines de servicio por cajero y luego llegadas por id.
Así, una llegada en el mismo instante que una salida observa el cajero ya
reasignado y espera. Al quedar libre un cajero, el motor asigna el siguiente
preferencial o, si no hay, el siguiente general; FCFS usa las mismas
etiquetas pero respeta el orden global de llegada. Una atención iniciada
nunca se corta. `reconstruir_tablero` devuelve un `EstadoTablero` inmutable y
`dibujar_tablero` no modifica la corrida, no simula y no sortea.

**Opcional no implementado:** controles de siguiente evento/reproducción
sobre el registro existente. No se generan nuevas llegadas ni servicios desde
la vista. Las esperas mostradas serían descriptivas de esa corrida, no
estimaciones estacionarias ni evidencia suficiente del número óptimo.

El tablero explica el mecanismo; las gráficas de espera por nivel, IC y
utilización sustentan las conclusiones. Ninguna animación reemplaza esas
comparaciones. Los datos son simulados (no mediciones de campo); solo los
fixtures de prueba son sintéticos y se rotulan como tales. La censura de
clientes en cola o servicio al instante mostrado sigue vigente, y sin τp/τg
no se elige capacidad óptima. Declaración de IA: docstrings, pruebas y
código D1/D2 se elaboraron con asistencia de IA. El equipo debe revisarlos y
adaptar la declaración al formato del curso; no se acredita cumplir su límite
del 20 % ni otras metas porcentuales no verificadas.
