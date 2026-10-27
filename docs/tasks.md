# Tareas del grupo

Un issue por integrante agrupa sus dos aportes. El orden es obligatorio:
A1 → A2 → B1 → B2 → C1 → C2 → D1 → D2. Cada aporte incluye sus propias
pruebas y documentación. [Tabla de commits](../contributing.md).

## Ivett — @ivecanahi — issue #1

- [x] **A1. Parámetros** (`src/modelo/parametros.py`): construir ambas familias
  sin mezclar tasas; validar μ>0, λ>0, c entero positivo, 0≤p≤1, horizonte
  mayor que calentamiento; verificar λp+λg=λ y estabilidad para contraste
  estacionario. Pruebas: unidades, valores documentados y rechazo inválido.
- [ ] **A2. Contratos** (`cliente.py`, `resultados.py`): niveles, identidad y
  marcas temporales; dos disciplinas; resultados por corrida con semilla,
  registros de eventos, métricas e ingresos/atendidos/pendientes por nivel.
  Pruebas de orden temporal y de estados incompletos. Un cliente con varias
  condiciones preferenciales cuenta una sola vez.

## Fernando — @Fede-dev11 — issue #2

Depende de #1.

- [ ] **B1. Estado** (`sistema.py`): cajeros compartidos y dos colas lógicas;
  prioridad no expropiativa, FCFS dentro de nivel, FCFS global en referencia.
  Pruebas deterministas: un preferencial no interrumpe; al liberar cajero
  precede al general; mismo nivel conserva orden; no queda cajero libre
  con espera. Definir desempate de eventos simultáneos.
- [ ] **B2. Motor** (`motor_des.py`): calendario DES, llegadas Poisson,
  servicios exponenciales con μ común, semillas reproducibles; entregar
  registros y áreas temporales de cola/ocupación en ventana medida.
  Cortar llegadas al horizonte, conservar pendientes y documentar si se
  drena el sistema; no incluir drenaje en denominadores de la ventana.
  Pruebas de conservación y reproducción exacta con misma semilla.

## Alex — @Alex-Francis-07 — issue #3

Depende de #1 y #2; el cálculo analítico puede prepararse tras #1.

- [ ] **C1. Analítico y métricas** (`src/modelo/analitico.py`, `metricas.py`):
  P0, Erlang C, Lq, L, Wq, W y ρ; rechazar contraste estacionario si ρ≥1.
  Caso de prueba M/M/1 λ=1, μ=2: ρ=0.5, Lq=0.5, Wq=0.5, L=1, W=1.
  Medir esperas por nivel y Lq temporal; contadores pendientes explícitos.
- [ ] **C2. Experimentos/CLI** (`src/control/experimentos.py`, `main.py`):
  familias × capacidades × FCFS/prioridad × réplicas, semillas registradas,
  calentamiento/horizonte configurables, CSV por réplica y resumen con IC95%.
  Usar mismas llegadas, etiquetas y servicios preasignados para comparar
  disciplinas (no solo misma semilla con consumos de RNG distintos).
  Contrastar agregado con Erlang C, ley de Little y conservación con
  tolerancias y efecto de bordes; no exigir igualdad exacta en corridas
  finitas. Probar CLI y CSV. No asignar Wq global a cada nivel ni modelar
  dos bancos independientes. Sin τp/τg: informar que no se puede seleccionar
  capacidad óptima. La regla mínima propuesta es menor c que cumpla ambos
  criterios, una vez definidos; reportar también utilización e incertidumbre.

## Jaime — @Jaimewww — issue #4

Depende de #3 y su formato de resultados.

- [ ] **D1. Figuras** (`src/vista/graficas.py`): espera por nivel y capacidad,
  FCFS/prioridad global contra analítico, utilización/ociosidad. Incluir
  unidades, leyendas, familia, p, réplicas e IC. Prueba con datos sintéticos
  rotulados como tales, sin presentarlos como resultados del estudio.
- [ ] **D2. Tablero e integración** (`src/vista/animacion.py`): dibujar estado
  de colas y cajeros desde eventos reales, reloj y leyenda; captura estática
  como mínimo, replay interactivo opcional. Verificar que no modifica
  resultados; ejecutar pipeline de ejemplo y documentar interpretación,
  límites, declaración de IA y resultados sin adelantar conclusiones.

## Decisiones antes de ejecutar experimentos

**Los criterios de espera τp y τg y la distribución entre las condiciones
preferenciales seguirán pendientes de respaldo o definición explícita como
supuestos experimentales.** No asignar porcentajes por condición ni umbrales
por defecto. No hace falta una distribución demográfica para el modelo de
dos niveles: los tres grupos comparten prioridad y μ común; si se añaden
etiquetas, evitar doble conteo y declarar el origen de sus proporciones.

Registrar p (fuente o supuesto), τp/τg (criterio explícito), unidad,
calentamiento, duración y réplicas. Una prueba piloto debe justificar estos
últimos, no convertir números arbitrarios en requisitos del documento.
Con μ común y atención no ociosa, la prioridad cambia el reparto de espera,
no garantiza una reducción global. Las comparaciones son estadísticas:
no exigir desigualdades estrictas por nivel en toda corrida.
