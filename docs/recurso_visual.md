# Recurso visual: tablero de colas y cajeros

**Propuesta para D2, todavía no implementada.** Un dibujo con Matplotlib
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
comparaciones. No hay comandos de exportación implementados todavía.
