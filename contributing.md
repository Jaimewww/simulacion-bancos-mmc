# Guía de contribución

## Orden de aportes

Cada integrante realiza **dos commits propios, consecutivos**, en el orden
siguiente. Los commits de preparación y registro de publicación del repositorio
son independientes: no cuentan como aportes académicos de Jaime ni reemplazan
el trabajo del grupo.
No se crean commits en nombre de otra persona.

| Orden | Integrante | GitHub | Tarea / issue | Commit propuesto | Aporte y verificación |
|---|---|---|---|---|---|
| 1 | Ivett Zaragocin | @ivecanahi | A1 / #1 | `feat(modelo): define validated scenarios (#1)` | Parámetros, familias, unidades y pruebas de validación |
| 2 | Ivett Zaragocin | @ivecanahi | A2 / #1 | `feat(modelo): define client and run records (#1)` | Cliente, niveles, resultados/eventos y pruebas |
| 3 | Fernando Patiño | @Fede-dev11 | B1 / #2 | `feat(modelo): implement shared teller queues (#2)` | Estado, FCFS/prioridad y pruebas deterministas |
| 4 | Fernando Patiño | @Fede-dev11 | B2 / #2 | `feat(modelo): implement discrete event engine (#2)` | Motor, semilla, integrales temporales y pruebas |
| 5 | Alex Sigcho | @Alex-Francis-07 | C1 / #3 | `feat(modelo): implement Erlang C metrics (#3)` | Analítico, métricas y pruebas con casos conocidos |
| 6 | Alex Sigcho | @Alex-Francis-07 | C2 / #3 | `feat(control): run replicated experiments (#3)` | Experimentos, CLI, CSV, IC y validación estadística |
| 7 | Jaime Landazuri | @Jaimewww | D1 / #4 | `feat(vista): plot experiment comparisons (#4)` | Figuras del informe y pruebas con datos de ejemplo |
| 8 | Jaime Landazuri | @Jaimewww | D2 / #4 | `feat(vista): display queue and teller board (#4)` | Tablero visual, integración final y prueba de ejemplo |

Los detalles y criterios de aceptación están en [tasks.md](docs/tasks.md).
Issues: [Ivett #1](https://github.com/Jaimewww/simulacion-bancos-mmc/issues/1),
[Fernando #2](https://github.com/Jaimewww/simulacion-bancos-mmc/issues/2),
[Alex #3](https://github.com/Jaimewww/simulacion-bancos-mmc/issues/3),
[Jaime #4](https://github.com/Jaimewww/simulacion-bancos-mmc/issues/4).

Se enviaron invitaciones de escritura a los tres colaboradores. Al publicar,
estaban pendientes: los issues #1–#3 identifican al responsable en el cuerpo,
pero su asignación formal queda pendiente de aceptar la invitación. Luego el
propietario debe asignarlos desde GitHub. #4 sí está asignado a @Jaimewww.
La configuración permite rebase merge y desactiva squash y merge commits;
no impone automáticamente los turnos, que el grupo debe respetar.

## Cómo conservar el orden

1. Esperar a que el integrante anterior publique sus dos commits.
2. Actualizar `main` con `git pull --ff-only` y crear una rama de trabajo.
3. Implementar únicamente las dos tareas del turno. Incluir pruebas y
   documentación con el comportamiento correspondiente, no como commits aparte.
4. Ejecutar las pruebas y publicar ambos commits juntos. Si se usa PR, hacer
   **fast-forward o rebase merge**, nunca squash ni merge commit adicional.
5. Verificar `git log --oneline` y avisar al siguiente integrante. No publicar
   aportes intercalados, commits vacíos ni commits con identidad ajena.

Cada autor configura su `user.name` y su propio correo verificado o `noreply`
de GitHub. Usar Conventional Commits. El segundo commit de cada turno puede
incluir `Closes #N` si todos los criterios del issue ya están comprobados.

## Verificación y límites

```bash
python3 -m unittest discover -s tests -v
```

Los módulos todavía son contratos pendientes, no una simulación operativa.
No cerrar un issue solo porque importe su módulo: ejecutar las pruebas de sus
reglas. El modelo no importa control ni vista; control orquesta; vista consume
resultados y no modifica el estado del motor. Los cambios de interfaz entre
turnos deben acordarse y documentarse antes del siguiente aporte.

Los criterios de espera τp y τg y la distribución entre las condiciones
preferenciales siguen pendientes de respaldo o definición explícita como
supuestos experimentales. Ningún aporte debe introducirlos como mediciones
ni fijarlos silenciosamente por defecto.

`p`, calentamiento, horizonte, repeticiones y umbrales de espera deben quedar
identificados como datos documentados o decisiones experimentales. No afirmar
un óptimo sin criterio explícito. Declarar la ayuda de IA conforme al curso;
ninguna herramienta garantiza por sí sola cumplir su límite del 20%.
