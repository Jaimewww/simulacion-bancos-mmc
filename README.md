# Simulación bancaria M/M/c con arquitectura MVC

Trabajo de Simulación, Universidad Nacional de Loja. Comparación de FCFS y
prioridad no expropiativa con cajeros compartidos. El proyecto incluye motor
de eventos discretos, métricas, experimentos con réplicas, seis figuras para
las dos familias y una interfaz local con replay y gráficas dinámicas.

## Arquitectura

| Capa | Ubicación | Responsabilidad |
|---|---|---|
| Modelo | `src/modelo/` | Parámetros, clientes, estado, DES, métricas y Erlang C |
| Controlador | `src/control/` | Experimentos, semillas, réplicas y exportación |
| Vista | `src/vista/` y `app_local.py` | Figuras, tablero, replay y gráficas dinámicas |
| Entrada | `main.py` | Asistente de experimentos y CLI avanzada |

El modelo no importa control ni vista. La vista consume resultados; no
elige al próximo cliente. El controlador no duplica la lógica de atención.

## Estructura actual

```text
PROYECTO U1/
├── resultados_experimentos/       # única carpeta de resultados
│   ├── replicas.csv
│   ├── resumen.csv
│   ├── metadata.json
│   └── figuras/                    # seis PNG al ejecutar ambas familias
└── simulacion-bancos-mmc/
    ├── app_local.py                # interfaz y gráficas en tiempo real
    ├── main.py                     # experimentos, exportación y figuras
    ├── requirements.txt
    ├── README.md
    ├── src/
    │   ├── control/
    │   │   ├── experimentos.py
    │   │   └── tablero.py
    │   ├── modelo/
    │   │   ├── analitico.py
    │   │   ├── cliente.py
    │   │   ├── metricas.py
    │   │   ├── motor_des.py
    │   │   ├── parametros.py
    │   │   ├── resultados.py
    │   │   └── sistema.py
    │   └── vista/
    │       ├── animacion.py
    │       └── graficas.py
    └── tests/                      # pruebas automatizadas
```

`.venv/`, `.git/` y `__pycache__/` se omiten del árbol porque son entorno,
control de versiones y caché, no código del sistema.

## Arranque y comprobación actuales

Python 3.10 o superior. B2 utiliza NumPy para el generador reproducible; crear
un entorno virtual e instalar las dependencias antes de ejecutar las pruebas.

Desde la raíz del repositorio, en Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
```

La CLI acepta `--familia adams_yeboah|marhamah|ambas`, `--solo-fcfs` y
`--solo-prioridad` (ambas banderas juntas ejecutan ambas disciplinas).
Las réplicas deben ser enteros positivos y la semilla base un entero >=0.
Errores de parámetros terminan con código 2. Se usa exclusivamente el paquete
`src.modelo`/`src.control`, sin modificar `sys.path` ni crear alias de módulos.
NumPy genera la carga y SciPy calcula cuantiles t; instalar `requirements.txt`.

### Generación sencilla de todos los resultados

Desde la carpeta del repositorio ejecuta `main.py` sin argumentos:

```bash
.venv/bin/python main.py
```

El propio programa ejecuta las dos familias y pregunta la proporción
preferencial y las réplicas. La proporción es la parte del total de clientes
que tiene prioridad: `p=0.25` significa 25 %. Todo se guarda en la única
carpeta `../resultados_experimentos/`, situada junto a `simulacion-bancos-mmc`,
donde se reemplazan automáticamente
`replicas.csv`, `resumen.csv`, `metadata.json` y las imágenes `d1_*.png` de
`figuras/`; no se acumulan versiones repetidas. También se puede usar la CLI
avanzada con argumentos. `main.py` genera las gráficas automáticamente, por lo
que ya no hace falta ejecutar otro comando.

Ejemplo avanzado equivalente:

```bash
.venv/bin/python main.py --familia ambas --p 0.25 --replicas 30
```

## Experimentos y métricas C1/C2

Las familias conservan sus unidades: horas para Adams/Yeboah y minutos para
Marhamah; horizonte, calentamiento, Wq y W usan esa unidad. Lq se expresa en
clientes y la utilización es una fracción. Por defecto se usan 8/1 horas o
480/60 minutos (horizonte/calentamiento). El asistente propone 30 réplicas y
p=0.25; la CLI avanzada conserva 10 y p=0.3 si se omiten. Son supuestos
experimentales, sin justificación piloto todavía. `--horizon` y
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

En `--salida` se crean tres archivos UTF-8 con nombres fijos. Cada ejecución
reemplaza los resultados generados anteriormente en esa carpeta, sin borrar
otros archivos del usuario:

- `replicas.csv`: escenario, disciplina, semilla, p/origen, unidad, ventana,
  conteos y pendientes separados por cola/servicio y nivel, Wq y tamaños de
  muestra, W/servicio por nivel, Lq, utilización y verificaciones de Little
  como JSON en `little_json`, además de `conservacion_ok`.
- `resumen.csv`: una fila por escenario/disciplina; cada métrica incluye
  `_media`, `_n`, `_ic95_inf`, `_ic95_sup`, `_metodo`, `_nota`; semillas y
  contraste Erlang C en `coherencia_json`. Son IC entre réplicas válidas.
- `metadata.json`: configuración, semillas, agregados, contrastes y
  verificaciones detalladas por réplica. No serializa objetos de corrida
  como cadenas opacas.

Estos formatos amplían la salida inicial de C2; D1 consume los campos
documentados. D2 no lee el CSV: reconstruye el tablero desde el registro de
eventos de una corrida real del motor. Los resultados son simulaciones bajo
supuestos, no mediciones bancarias. La duración/calentamiento y el número de réplicas
requieren estudio piloto antes de sacar conclusiones del estudio.

## Figuras D1 (vista)

```bash
.venv/bin/python -m src.vista.graficas ../resultados_experimentos/resumen.csv --salida ../resultados_experimentos/figuras
```

La vista consume `resumen.csv` de C2 y no simula ni recalcula: los
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

`main.py` ya genera las figuras automáticamente. El comando anterior queda
disponible para regenerarlas desde el resumen sin repetir las simulaciones.

## Tablero D2 (vista)

Ejemplo de una captura estática independiente:

```bash
.venv/bin/python -m src.control.tablero --familia marhamah --c 3 --p 0.3 --origen-p "supuesto de sensibilidad" --horizon 480 --warmup 60 --semilla 12345 --instante 300 --salida ../resultados_experimentos/tablero.png
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
interactivo se implementó posteriormente en la vista local Python descrita
más adelante; reutiliza este mismo registro de eventos y no contiene un
segundo simulador.

**Declaración de IA.** Para D1/D2 y la vista local se utilizó asistencia de IA en código,
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

- Orden de los ocho aportes: Ivett → Fernando → Alex → Jaime.

### Tareas y criterios de aceptación

Cada issue agrupó dos aportes consecutivos, con sus propias pruebas y
documentación. El orden obligatorio fue A1 → A2 → B1 → B2 → C1 → C2 → D1 →
D2.

- **Ivett — issue #1.** A1 implementó parámetros, familias, unidades,
  validaciones, descomposición `λp + λg = λ` y estabilidad. A2 implementó
  clientes, niveles, identidad, marcas temporales, eventos, disciplinas y
  resultados por corrida. Un cliente con varias condiciones preferenciales
  se cuenta una sola vez.
- **Fernando — issue #2.** B1 implementó cajeros compartidos, dos colas
  lógicas, prioridad no expropiativa, FCFS por nivel y FCFS global. Sus pruebas
  verifican precedencia, no interrupción, orden y ausencia de cajeros ociosos
  con clientes esperando. B2 implementó el calendario DES, carga Poisson,
  servicios exponenciales, semillas reproducibles, registro de eventos y
  áreas temporales. La corrida corta llegadas en el horizonte, no drena y
  conserva pendientes.
- **Alex — issue #3.** C1 implementó P0, Erlang C, Lq, L, Wq, W, utilización,
  métricas por nivel y contadores pendientes; el contraste estacionario se
  rechaza con `ρ≥1`. C2 implementó la matriz de familias, capacidades,
  disciplinas y réplicas, compartiendo carga preasignada entre FCFS y
  prioridad. Exporta CSV/JSON, IC95 %, semillas y comprobaciones de Erlang C,
  Little y conservación. Sin `τp`/`τg` no selecciona capacidad óptima.
- **Jaime — issue #4.** D1 implementó figuras de espera por nivel, contraste
  global con Erlang C y utilización/ociosidad, con unidades, leyendas, p,
  réplicas e intervalos. Los fixtures inventados se rotulan como sintéticos.
  D2 reconstruye el tablero de cajeros y colas desde eventos reales, sin
  modificar la corrida. Incluye reloj, leyenda, captura estática y replay
  interactivo local.

Antes de interpretar los experimentos deben registrarse p y su origen,
unidad, calentamiento, duración, réplicas y los criterios `τp`/`τg` si se
definen. Una prueba piloto debe justificar duración, calentamiento y número
de réplicas. La prioridad redistribuye la espera, pero no garantiza una
reducción global. No se inventan proporciones por condición demográfica ni se
exigen desigualdades estrictas en cada corrida finita.

### Vista local interactiva en Python

La interfaz utiliza directamente `ParametrosEscenario`, `MotorDES`,
`ResultadoCorrida` y `reconstruir_tablero`; no contiene un motor JavaScript ni
requiere servidor web.

```bash
.venv/bin/python app_local.py
```

Permite editar tasas, semilla, disciplina, horizonte, velocidad y entre 1 y
24 cajeros. Las dos colas y la tabla de cajeros tienen desplazamiento. El
replay se construye exclusivamente con eventos del backend. Las gráficas se
muestran al lado derecho del tablero y avanzan con el mismo reloj: presentan
la ocupación hasta el instante actual y la capacidad ocupada/libre. También
muestran `ρ` teórico y el estado estable o saturado del escenario.

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
