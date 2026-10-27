"""Estado de un sistema con dos colas y un conjunto de cajeros compartidos.

Responsable: Fernando Patiño (@Fede-dev11) — Tarea #2, commit B1.

La prioridad es no expropiativa: una llegada preferencial nunca interrumpe un
servicio en curso. Al quedar libre un cajero, PRIORIDAD elige primero la cola
preferencial y FCFS elige la llegada más antigua sin considerar el nivel.

El motor B2 procesará eventos simultáneos en este orden: finalizaciones de
servicio, por número de cajero, y después llegadas, por ``id_llegada``. Así,
una finalización puede asignar inmediatamente a alguien que ya esperaba; una
llegada en ese mismo instante observa el estado resultante.
"""

from collections import deque
from types import MappingProxyType

from .cliente import Cliente, EstadoCliente, Nivel
from .resultados import Disciplina


class Sistema:
    """Administra colas FIFO y la ocupación de ``c`` cajeros idénticos."""

    def __init__(self, c: int, disciplina: Disciplina = Disciplina.PRIORIDAD) -> None:
        if not isinstance(c, int) or isinstance(c, bool) or c <= 0:
            raise ValueError(f"c debe ser un entero positivo: {c!r}")
        if not isinstance(disciplina, Disciplina):
            raise ValueError(f"disciplina debe ser Disciplina: {disciplina!r}")
        self.c = c
        self.disciplina = disciplina
        self._preferenciales: deque[Cliente] = deque()
        self._generales: deque[Cliente] = deque()
        self._ocupados: dict[int, Cliente] = {}
        self._registrados: dict[int, Cliente] = {}

    @property
    def ocupados(self):
        """Mapa de solo lectura ``cajero -> cliente`` actualmente atendido."""
        return MappingProxyType(self._ocupados)

    @property
    def cantidad_ocupados(self) -> int:
        return len(self._ocupados)

    def hay_cajero_libre(self) -> bool:
        return self.cantidad_ocupados < self.c

    def _cajero_libre(self) -> int | None:
        return next((numero for numero in range(self.c) if numero not in self._ocupados), None)

    def _cola(self, nivel: Nivel) -> deque[Cliente]:
        if nivel is Nivel.PREFERENCIAL:
            return self._preferenciales
        if nivel is Nivel.GENERAL:
            return self._generales
        raise ValueError(f"nivel desconocido: {nivel!r}")

    def _registrar(self, cliente: Cliente) -> None:
        if not isinstance(cliente, Cliente):
            raise TypeError(f"cliente debe ser Cliente: {cliente!r}")
        if cliente.id_llegada in self._registrados:
            raise ValueError(f"cliente ya registrado: {cliente.id_llegada}")
        if cliente.estado is not EstadoCliente.EN_COLA:
            raise ValueError(f"cliente {cliente.id_llegada} ya inició servicio")
        self._registrados[cliente.id_llegada] = cliente

    def encolar(self, cliente: Cliente) -> None:
        """Añade una espera conservando FCFS dentro de su nivel."""
        self._registrar(cliente)
        cola = self._cola(cliente.nivel)
        clave = (cliente.t_llegada, cliente.id_llegada)
        if cola and clave < (cola[-1].t_llegada, cola[-1].id_llegada):
            del self._registrados[cliente.id_llegada]
            raise ValueError("las llegadas deben encolarse en orden cronológico")
        cola.append(cliente)

    def recibir(self, cliente: Cliente, t: float) -> int | None:
        """Inicia una llegada si hay cajero; si no, la deja esperando."""
        if self.hay_cajero_libre():
            return self.iniciar_servicio(cliente, t)
        self.encolar(cliente)
        return None

    def siguiente_cliente(self) -> Cliente | None:
        """Extrae el siguiente cliente según la disciplina configurada."""
        if self.disciplina is Disciplina.PRIORIDAD:
            if self._preferenciales:
                return self._preferenciales.popleft()
            if self._generales:
                return self._generales.popleft()
            return None

        candidatos = [cola[0] for cola in (self._preferenciales, self._generales) if cola]
        if not candidatos:
            return None
        siguiente = min(candidatos, key=lambda item: (item.t_llegada, item.id_llegada))
        return self._cola(siguiente.nivel).popleft()

    def iniciar_servicio(
        self, cliente: Cliente, t: float, cajero: int | None = None
    ) -> int:
        """Asigna un cajero libre y mueve al cliente a servicio."""
        if not isinstance(cliente, Cliente):
            raise TypeError(f"cliente debe ser Cliente: {cliente!r}")
        registrado = self._registrados.get(cliente.id_llegada)
        if registrado is not None and registrado is not cliente:
            raise ValueError(f"cliente ya registrado: {cliente.id_llegada}")
        nuevo = registrado is None
        if cliente.estado is not EstadoCliente.EN_COLA:
            raise ValueError(f"cliente {cliente.id_llegada} no está en cola")
        if cajero is None:
            cajero = self._cajero_libre()
        if not isinstance(cajero, int) or isinstance(cajero, bool):
            raise ValueError(f"cajero debe ser un entero: {cajero!r}")
        if not 0 <= cajero < self.c:
            raise ValueError(f"cajero fuera de rango: {cajero!r}")
        if cajero in self._ocupados:
            raise ValueError(f"cajero {cajero} está ocupado")

        if nuevo:
            self._registrar(cliente)

        cola = self._cola(cliente.nivel)
        for indice, esperando in enumerate(cola):
            if esperando is cliente:
                del cola[indice]
                break
        try:
            cliente.iniciar_servicio(t, cajero)
        except (TypeError, ValueError):
            if nuevo:
                del self._registrados[cliente.id_llegada]
            raise
        self._ocupados[cajero] = cliente
        return cajero

    def finalizar_servicio(self, cliente: Cliente, t: float) -> Cliente | None:
        """Finaliza y asigna inmediatamente el mismo cajero si alguien espera."""
        if not isinstance(cliente, Cliente):
            raise TypeError(f"cliente debe ser Cliente: {cliente!r}")
        cajero = cliente.cajero
        if cajero is None or self._ocupados.get(cajero) is not cliente:
            raise ValueError(f"cliente {cliente.id_llegada} no ocupa un cajero del sistema")
        cliente.finalizar_servicio(t)
        del self._ocupados[cajero]
        siguiente = self.siguiente_cliente()
        if siguiente is not None:
            self.iniciar_servicio(siguiente, t, cajero)
        return siguiente

    def longitud_colas(self) -> tuple[int, int]:
        """Devuelve ``(preferenciales, generales)`` esperando."""
        return len(self._preferenciales), len(self._generales)

    def utilizacion_instantanea(self) -> float:
        return self.cantidad_ocupados / self.c
