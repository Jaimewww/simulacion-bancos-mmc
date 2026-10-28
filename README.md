# Simulación bancaria M/M/c con arquitectura MVC

Trabajo de Simulación, Universidad Nacional de Loja. Comparación de FCFS y
prioridad no expropiativa con cajeros compartidos. **Estado: B1 y B2
implementados; C1/C2 incluyen métricas, experimentos y CLI; D1 genera las
figuras del informe y D2 el tablero estático desde eventos reales.**

## Arquitectura

| Capa | Ubicación | Responsabilidad |
|---|---|---|
| Modelo | `src/modelo/` | Parámetros, clientes, estado, DES, métricas y Erlang C |
| Controlador | `src/control/` | Experimentos, semillas, réplicas y exportación |
| Vista | `src/vista/` | Gráficas y tablero de colas/cajeros |
| Entrada | `main.py` | CLI que invoca al controlador |

El modelo no importa control ni vista. La vista consume resultados; no
elige al próximo cliente. El controlador no duplica la lógica de atención.

## Arranque y comprobación actuales

Python 3.10 o superior. B2 utiliza NumPy para el generador reproducible; crear
un entorno virtual e instalar las dependencias antes de ejecutar las pruebas.

Desde la raíz, en PowerShell (sin `PYTHONPATH`):

```powershell
.venv/Scripts/python.exe -m pip install -r requirements.txt
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe main.py --help
.venv/Scripts/python.exe main.py --familia marhamah --p 0.3 --origen-p "supuesto de sensibilidad, no medicion" --horizon 480 --warmup 60 --replicas 10 --semilla-base 12345 --salida resultados_experimentos
```

La CLI acepta `--familia adams_yeboah|marhamah|ambas`, `--solo-fcfs` y
`--solo-prioridad` (ambas banderas juntas ejecutan ambas disciplinas).
Las réplicas deben ser enteros positivos y la semilla base un entero >=0.
Errores de parámetros terminan con código 2. Se usa exclusivamente el paquete
`src.modelo`/`src.control`, sin modificar `sys.path` ni crear alias de módulos.
NumPy genera la carga y SciPy calcula cuantiles t; instalar `requirements.txt`.

## Experimentos y métricas C1/C2

Las familias conservan sus unidades: horas para Adams/Yeboah y minutos para
Marhamah; horizonte, calentamiento, Wq y W usan esa unidad. Lq se expresa en
clientes y la utilización es una fracción. Por defecto se usan 8/1 horas o
480/60 minutos (horizonte/calentamiento), 10 réplicas y p=0.3, rotulados como
supuestos experimentales, sin justificación piloto todavía. `--horizon` y
`--warmup` se aplican en la unidad propia de cada familia, también con `ambas`.
`--origen-p` registra la fuente o el supuesto declarado; no se inventan
proporciones por condición demográfica. Sin tau_p y tau_g no se selecciona
capacidad óptima.

Cada réplica preasigna llegadas, niveles y servicios con semilla base+i antes
de aplicar la disciplina. Ambas disciplinas comparten esos datos, cajeros y
mu; no se simulan dos bancos separados. Las réplicas usan semillas distintas.

Las medias de clientes seleccionan llegadas en `[warmup, horizon]`: Wq usa
solo quienes iniciaron servicio, W y servicio medio solo quienes terminaron.
El Wq global pondera cada cliente observado, no promedia medias de niveles.
Un nivel sin observaciones conserva `None`, exportado como celda vacía.
Los clientes aún en cola tienen espera final desconocida; los que están en
servicio tienen Wq conocido y permanencia final desconocida. Esta censura
puede sesgar las medias hacia abajo. No hay drenaje.

Las integrales Lq y utilización miden todo el estado en `[warmup, horizon]`,
incluidos clientes llegados antes del calentamiento. Por ello no son medias
de la cohorte. Little se ejecuta por réplica, por nivel y global: compara Lq
con tasa de llegadas observada de la cohorte por Wq. Reporta valores y
diferencias con tolerancia relativa exploratoria del 20% (escala máxima de
ambos lados), que no constituye aceptación estadística. Censura, arrastre
inicial y horizonte finito impiden exigir igualdad. Además se reconstruye
la integral con cada espera recortada a la ventana, incluyendo pendientes:
esta identidad debe coincidir a tolerancia numérica 1e-9. Conservación usa
flujos de eventos y estados por nivel, con diferencias enteras exactamente
cero. Una discrepancia se reporta, no se oculta.

El resumen usa medias de réplicas, IC95% t de Student con n-1 grados de
libertad y n válido por métrica; con n<2 no calcula límites. Supone réplicas
independientes y medias aproximadamente normales; pocas réplicas, censura
y sesgo transitorio limitan la interpretación. El contraste agregado compara
Wq global, Lq y utilización con Erlang C (solo rho<1), reportando diferencias
y si el teórico cae en el IC. Esto no prueba equivalencia ni corrige el sesgo
de bordes; hay comparaciones múltiples. No se asigna Erlang C global a niveles.

En `--salida` se crean archivos UTF-8 con marca temporal:

- `replicas_*.csv`: escenario, disciplina, semilla, p/origen, unidad, ventana,
  conteos y pendientes separados por cola/servicio y nivel, Wq y tamaños de
  muestra, W/servicio por nivel, Lq, utilización y verificaciones de Little
  como JSON en `little_json`, además de `conservacion_ok`.
- `resumen_*.csv`: una fila por escenario/disciplina; cada métrica incluye
  `_media`, `_n`, `_ic95_inf`, `_ic95_sup`, `_metodo`, `_nota`; semillas y
  contraste Erlang C en `coherencia_json`. Son IC entre réplicas válidas.
- `metadata_*.json`: configuración, semillas, agregados, contrastes y
  verificaciones detalladas por réplica. No serializa objetos de corrida
  como cadenas opacas.

Estos formatos amplían la salida inicial de C2; D1 consume los campos
documentados. D2 no lee el CSV: reconstruye el tablero desde el registro de
eventos de una corrida real del motor. Los resultados son simulaciones bajo
supuestos, no mediciones bancarias. La duración/calentamiento y el número de réplicas
requieren estudio piloto antes de sacar conclusiones del estudio.

## Figuras D1 (vista)

```powershell
.venv/Scripts/python.exe -m src.vista.graficas salidas/experimentos/resumen_<marca>.csv --salida salidas/figuras
```

La vista consume un `resumen_*.csv` de C2 y no simula ni recalcula: los
teóricos se copian de `coherencia_json`. Por familia crea
`d1_<familia>_wq_niveles.png`, `_wq_global_erlang.png` y
`_utilizacion_ociosidad.png`: Wq por nivel con FCFS y prioridad, Wq global
contra Erlang C, y ρ con ociosidad 1-ρ (extremos del IC girados: 1-sup,
1-inf). Cada figura rotula familia, unidad, p/origen_p, réplicas e IC95 %; una
celda vacía no se dibuja como cero y con n<2 no hay barra de IC. Familias y
unidades se separan; mezclarlas dentro de una familia es un error de entrada.
`--sintetico` solo agrega el rótulo "datos sintéticos: no son resultados del
estudio". El backend lo elige el entorno (`MPLBACKEND=Agg` en pruebas) y la
CLI cierra las figuras. Son figuras descriptivas: sin τp/τg no se elige
capacidad óptima.

## Tablero D2 (vista)

Cadena completa de ejemplo (una sola corrida real por tablero):

```powershell
# 1) experimentos C2 -> CSV de réplicas y resumen
.venv/Scripts/python.exe main.py --familia marhamah --p 0.3 --origen-p "supuesto de sensibilidad, no medicion" --horizon 480 --warmup 60 --replicas 10 --semilla-base 12345 --salida salidas/experimentos
# 2) figuras D1 desde el resumen recién creado (usar la marca de tiempo)
.venv/Scripts/python.exe -m src.vista.graficas salidas/experimentos/resumen_<marca>.csv --salida salidas/figuras
# 3) tablero D2 desde una corrida real del motor
.venv/Scripts/python.exe -m src.control.tablero --familia marhamah --c 3 --p 0.3 --origen-p "supuesto de sensibilidad, no medicion" --horizon 480 --warmup 60 --semilla 12345 --instante 300 --salida salidas/tablero/tablero.png
```

`--p`, `--origen-p`, `--horizon` y `--warmup` son obligatorios: no hay valores
inventados. `--familia`, `--c`, `--semilla`, `--disciplina`, `--instante` y
`--salida` tienen valores documentados en `--help`. Si se omite `--instante`
se dibuja el horizonte y el rótulo lo dice. Una entrada inválida (p fuera de
[0,1], c fuera de la familia, instante negativo o posterior al horizonte)
termina con código 2 antes de crear el PNG.

El tablero reconstruye todos los eventos con `t <= instante` en el orden del
registro y muestra cajeros ocupados/libres con el id de cliente, las dos
colas en orden de atención con etiquetas P/G y conteos, el reloj con unidad,
la disciplina, familia, semilla y p/`origen_p`. La vista no simula, no sortea,
no reordena y no modifica la corrida: solo lee `ResultadoCorrida`. Un `None`
se conserva: cajero libre, cola vacía y τp/τg "no definido".

**Qué es y qué no es.** Los datos son **simulados** por el motor M/M/c bajo
supuestos (Poisson, servicios exponenciales, sin abandono ni rechazo); no hay
datos de **campo** ni mediciones del banco. Solo los fixtures de prueba son
**sintéticos** y se rotulan así. El tablero es una captura estática
descriptiva de una corrida: no estima esperas estacionarias, no aporta IC y
no elige capacidad óptima. La censura sigue presente: clientes en cola o en
servicio al instante mostrado tienen resultados incompletos. El replay
event-by-event (interactivo) **no está implementado**; queda como opcional.

**Declaración de IA.** Para D1/D2 se utilizó asistencia de IA en código,
pruebas y documentación. El equipo debe revisar, comprender y adaptar esta
declaración al formato del curso. No se acredita automáticamente cumplir
el límite de uso de IA del 20 % ni se atribuye un origen no verificado al
resto del código. Los parámetros de referencia proceden del documento
académico; no se inventan mediciones ni proporciones demográficas.

## Contratos del modelo (issue #1)

- A1, `parametros.py`: `ParametrosEscenario` inmutable y validado con unidad
  explícita (`Unidad.HORA`/`Unidad.MINUTO`), `ADAMS_YEBOAH`, `MARHAMAH`,
  `familia_*`, `escenarios_familia`, ρ y `exigir_estabilidad()` (ρ<1),
  `en_unidad()` para convertir. p, `origen_p`, horizonte y calentamiento
  son obligatorios; réplicas y τp/τg quedan `None` (pendientes) por defecto.
- A2, `cliente.py`/`resultados.py`: `Cliente` con estados en cola/en
  servicio/atendido (esperas `None` si no aplican), condiciones
  preferenciales sin doble conteo, `Evento`/`TipoEvento` con registro no
  decreciente, `ConteoNivel` y `ResultadoCorrida` con semilla y disciplina.
- B1, `sistema.py`: cajeros compartidos, colas FIFO por nivel, FCFS global y
  prioridad no expropiativa. Una liberación asigna inmediatamente al siguiente
  cliente. En eventos simultáneos, B2 procesará primero las finalizaciones por
  cajero y luego las llegadas por `id_llegada`.
- B2, `motor_des.py`: carga Poisson y servicios exponenciales reproducibles,
  calendario de eventos, registro para replay e integrales de cola/ocupación.
  La corrida se detiene sin drenaje en el horizonte y conserva los pendientes;
  los denominadores usan solo la ventana posterior al calentamiento.

## Trabajo del grupo

- [Orden de los ocho commits](contributing.md): Ivett → Fernando → Alex → Jaime.
- [Tareas y criterios de aceptación](docs/tasks.md).
- [Recurso visual y tablero](docs/recurso_visual.md).
- [Vista local interactiva en Python](docs/vista_local.md), conectada
  directamente al motor y al registro de eventos del modelo.
- Documento académico original: `Simulación_Bancos.docx`.

Dos familias separadas: Adams/Yeboah (45 clientes/h, 12 clientes/h/cajero,
c=8…12) y Marhamah (0.3246 clientes/min, 0.2839 clientes/min/cajero, c=2…5).
Se conservará la unidad de cada escenario o se convertirá explícitamente.
Las tasas aquí son las citadas por el documento, no observaciones del grupo
ni una auditoría independiente de las fuentes.

**Pendiente:** los criterios de espera τp y τg y la distribución entre las
condiciones preferenciales seguirán pendientes de respaldo o definición
explícita como supuestos experimentales. Tampoco se fija una proporción
preferencial total p sin fuente o supuesto declarado. No inventar mediciones
ni repartir porcentajes entre adultos mayores, discapacidad y embarazo;
las tres condiciones comparten el mismo nivel de prioridad. Los valores de sensibilidad se rotularán como supuestos. La
prioridad no interrumpe servicios y mantiene FCFS dentro de cada nivel.
Sin abandono, rechazo ni cajeros exclusivos. No declarar un número óptimo
hasta fijar un criterio para ambos niveles.
