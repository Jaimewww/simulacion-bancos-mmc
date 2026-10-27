# Simulación bancaria M/M/c — esqueleto MVC

Trabajo de Simulación, Universidad Nacional de Loja. Comparación de FCFS y
prioridad no expropiativa con cajeros compartidos. **Estado: B1 implementado;
el motor, los experimentos y las vistas todavía no están implementados.**

## Arquitectura

| Capa | Ubicación | Responsabilidad |
|---|---|---|
| Modelo | `src/modelo/` | Parámetros, clientes, estado, DES, métricas y Erlang C |
| Controlador | `src/control/` | Experimentos, semillas, réplicas y exportación |
| Vista | `src/vista/` | Gráficas y tablero de colas/cajeros |
| Entrada | `main.py` | Futura CLI que invoca al controlador |

El modelo no importa control ni vista. La vista consume resultados; no
elige al próximo cliente. El controlador no duplica la lógica de atención.

## Arranque y comprobación actuales

Python 3.10 o superior. Las pruebas del esqueleto no necesitan dependencias.

```bash
python3 -m unittest discover -s tests -v
python3 main.py --help
python3 main.py
```

El último comando termina con código 2 e informa que la simulación está
pendiente. No genera resultados ni acepta todavía opciones de escenarios.
Para la implementación posterior: crear un entorno virtual e instalar
`requirements.txt` (NumPy, Matplotlib y pandas; `unittest` viene con Python).

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

## Trabajo del grupo

- [Orden de los ocho commits](contributing.md): Ivett → Fernando → Alex → Jaime.
- [Tareas y criterios de aceptación](docs/tasks.md).
- [Propuesta del recurso visual](docs/recurso_visual.md).
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
