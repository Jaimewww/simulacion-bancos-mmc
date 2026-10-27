"""Client and run-result contracts (task A2, issue #1).

All timestamps and counts are hand-written test inputs, not study results.
"""

import math
import unittest

from src.modelo.cliente import (
    Cliente,
    CondicionPreferencial,
    EstadoCliente,
    Nivel,
    nivel_por_condiciones,
)
from src.modelo.parametros import Unidad, familia_marhamah
from src.modelo.resultados import (
    ConteoNivel,
    Disciplina,
    Evento,
    ResultadoCorrida,
    TipoEvento,
    contar_por_nivel,
    validar_registro_eventos,
)

ADULTO, DISC, EMB = (
    CondicionPreferencial.ADULTO_MAYOR,
    CondicionPreferencial.DISCAPACIDAD,
    CondicionPreferencial.EMBARAZO,
)


class NivelTests(unittest.TestCase):
    def test_every_condition_shares_the_preferential_level(self):
        for condicion in CondicionPreferencial:
            with self.subTest(condicion=condicion):
                self.assertIs(nivel_por_condiciones([condicion]), Nivel.PREFERENCIAL)
        self.assertIs(nivel_por_condiciones([]), Nivel.GENERAL)

    def test_multiple_conditions_count_once(self):
        cliente = Cliente.desde_condiciones(1, 0.0, [ADULTO, DISC, EMB, ADULTO])
        self.assertIs(cliente.nivel, Nivel.PREFERENCIAL)
        self.assertEqual(cliente.condiciones, frozenset({ADULTO, DISC, EMB}))
        conteos = contar_por_nivel([cliente])
        self.assertEqual(conteos[Nivel.PREFERENCIAL].ingresados, 1)
        self.assertEqual(conteos[Nivel.GENERAL].ingresados, 0)

    def test_general_client_cannot_carry_conditions(self):
        with self.assertRaises(ValueError):
            Cliente(id_llegada=1, nivel=Nivel.GENERAL, t_llegada=0.0,
                    condiciones=frozenset({EMB}))

    def test_preferential_label_without_condition_detail_is_allowed(self):
        cliente = Cliente(id_llegada=1, nivel=Nivel.PREFERENCIAL, t_llegada=0.0)
        self.assertEqual(cliente.condiciones, frozenset())


class ClienteTemporalTests(unittest.TestCase):
    def test_complete_lifecycle(self):
        cliente = Cliente(id_llegada=7, nivel=Nivel.GENERAL, t_llegada=1.0)
        self.assertIs(cliente.estado, EstadoCliente.EN_COLA)
        cliente.iniciar_servicio(3.5, cajero=2)
        self.assertIs(cliente.estado, EstadoCliente.EN_SERVICIO)
        self.assertEqual(cliente.cajero, 2)
        cliente.finalizar_servicio(6.0)
        self.assertIs(cliente.estado, EstadoCliente.ATENDIDO)
        self.assertAlmostEqual(cliente.t_espera, 2.5)
        self.assertAlmostEqual(cliente.t_servicio, 2.5)
        self.assertAlmostEqual(cliente.t_sistema, 5.0)

    def test_zero_wait_is_valid(self):
        cliente = Cliente(id_llegada=1, nivel=Nivel.GENERAL, t_llegada=2.0)
        cliente.iniciar_servicio(2.0, cajero=0)
        self.assertEqual(cliente.t_espera, 0.0)

    def test_incomplete_states_return_none(self):
        en_cola = Cliente(id_llegada=1, nivel=Nivel.GENERAL, t_llegada=4.0)
        self.assertIsNone(en_cola.t_espera)
        self.assertIsNone(en_cola.t_servicio)
        self.assertIsNone(en_cola.t_sistema)
        self.assertIsNone(en_cola.cajero)
        en_servicio = Cliente(id_llegada=2, nivel=Nivel.PREFERENCIAL, t_llegada=1.0,
                              t_inicio_servicio=2.0, cajero=0)
        self.assertIs(en_servicio.estado, EstadoCliente.EN_SERVICIO)
        self.assertEqual(en_servicio.t_espera, 1.0)
        self.assertIsNone(en_servicio.t_sistema)
        self.assertIsNone(en_servicio.t_servicio)

    def test_start_before_arrival_is_rejected(self):
        cliente = Cliente(id_llegada=1, nivel=Nivel.GENERAL, t_llegada=5.0)
        with self.assertRaises(ValueError):
            cliente.iniciar_servicio(4.9, cajero=0)
        self.assertIs(cliente.estado, EstadoCliente.EN_COLA)
        with self.assertRaises(ValueError):
            Cliente(id_llegada=1, nivel=Nivel.GENERAL, t_llegada=5.0,
                    t_inicio_servicio=4.0, cajero=0)

    def test_end_before_start_is_rejected(self):
        cliente = Cliente(id_llegada=1, nivel=Nivel.GENERAL, t_llegada=0.0)
        cliente.iniciar_servicio(2.0, cajero=0)
        with self.assertRaises(ValueError):
            cliente.finalizar_servicio(1.0)
        self.assertIs(cliente.estado, EstadoCliente.EN_SERVICIO)

    def test_invalid_transitions_are_rejected(self):
        cliente = Cliente(id_llegada=1, nivel=Nivel.GENERAL, t_llegada=0.0)
        with self.assertRaises(ValueError):
            cliente.finalizar_servicio(1.0)
        cliente.iniciar_servicio(1.0, cajero=0)
        with self.assertRaises(ValueError):
            cliente.iniciar_servicio(1.5, cajero=1)
        with self.assertRaises(ValueError):
            Cliente(id_llegada=1, nivel=Nivel.GENERAL, t_llegada=0.0,
                    t_fin_servicio=3.0)

    def test_teller_must_match_service_start(self):
        with self.assertRaises(ValueError):
            Cliente(id_llegada=1, nivel=Nivel.GENERAL, t_llegada=0.0, cajero=0)
        with self.assertRaises(ValueError):
            Cliente(id_llegada=1, nivel=Nivel.GENERAL, t_llegada=0.0,
                    t_inicio_servicio=1.0)
        cliente = Cliente(id_llegada=1, nivel=Nivel.GENERAL, t_llegada=0.0)
        for cajero in (-1, 1.0, True):
            with self.subTest(cajero=cajero), self.assertRaises(ValueError):
                cliente.iniciar_servicio(1.0, cajero=cajero)

    def test_invalid_identity_level_or_time(self):
        casos = (
            dict(id_llegada=-1, nivel=Nivel.GENERAL, t_llegada=0.0),
            dict(id_llegada=True, nivel=Nivel.GENERAL, t_llegada=0.0),
            dict(id_llegada=1, nivel=1, t_llegada=0.0),
            dict(id_llegada=1, nivel=Nivel.GENERAL, t_llegada=-0.1),
            dict(id_llegada=1, nivel=Nivel.GENERAL, t_llegada=math.nan),
        )
        for datos in casos:
            with self.subTest(datos=datos), self.assertRaises(ValueError):
                Cliente(**datos)


class EventoTests(unittest.TestCase):
    def test_event_fields(self):
        evento = Evento(instante=1.5, tipo=TipoEvento.INICIO_SERVICIO,
                        cliente_id=3, cajero=1)
        self.assertEqual((evento.instante, evento.cliente_id, evento.cajero), (1.5, 3, 1))

    def test_teller_presence_depends_on_event_type(self):
        with self.assertRaises(ValueError):
            Evento(instante=0.0, tipo=TipoEvento.LLEGADA, cliente_id=1, cajero=0)
        with self.assertRaises(ValueError):
            Evento(instante=0.0, tipo=TipoEvento.FIN_SERVICIO, cliente_id=1)

    def test_invalid_event_values(self):
        with self.assertRaises(ValueError):
            Evento(instante=-1.0, tipo=TipoEvento.LLEGADA, cliente_id=1)
        with self.assertRaises(ValueError):
            Evento(instante=0.0, tipo="llegada", cliente_id=1)

    def test_log_must_be_non_decreasing(self):
        ordenado = [
            Evento(instante=0.0, tipo=TipoEvento.LLEGADA, cliente_id=1),
            Evento(instante=0.0, tipo=TipoEvento.INICIO_SERVICIO, cliente_id=1, cajero=0),
            Evento(instante=2.0, tipo=TipoEvento.FIN_SERVICIO, cliente_id=1, cajero=0),
        ]
        self.assertEqual(validar_registro_eventos(ordenado), tuple(ordenado))
        with self.assertRaises(ValueError):
            validar_registro_eventos(list(reversed(ordenado)))


def _corrida_ejemplo():
    atendido = Cliente(id_llegada=1, nivel=Nivel.GENERAL, t_llegada=0.0)
    preferencial = Cliente.desde_condiciones(2, 0.5, [ADULTO, EMB])
    en_cola = Cliente(id_llegada=3, nivel=Nivel.GENERAL, t_llegada=1.0)
    atendido.iniciar_servicio(0.0, cajero=0)
    preferencial.iniciar_servicio(0.5, cajero=1)
    atendido.finalizar_servicio(2.0)
    eventos = [
        Evento(instante=0.0, tipo=TipoEvento.LLEGADA, cliente_id=1),
        Evento(instante=0.0, tipo=TipoEvento.INICIO_SERVICIO, cliente_id=1, cajero=0),
        Evento(instante=0.5, tipo=TipoEvento.LLEGADA, cliente_id=2),
        Evento(instante=0.5, tipo=TipoEvento.INICIO_SERVICIO, cliente_id=2, cajero=1),
        Evento(instante=1.0, tipo=TipoEvento.LLEGADA, cliente_id=3),
        Evento(instante=2.0, tipo=TipoEvento.FIN_SERVICIO, cliente_id=1, cajero=0),
    ]
    return [atendido, preferencial, en_cola], eventos


def _parametros():
    return familia_marhamah(2, 0.3, origen_p="supuesto de prueba",
                            horizon=3.0, warmup=0.0)


class ConteoTests(unittest.TestCase):
    def test_counts_by_level_are_consistent(self):
        clientes, _ = _corrida_ejemplo()
        conteos = contar_por_nivel(clientes)
        self.assertEqual(conteos[Nivel.GENERAL], ConteoNivel(2, 1, 1))
        self.assertEqual(conteos[Nivel.PREFERENCIAL], ConteoNivel(1, 0, 1))
        for conteo in conteos.values():
            self.assertEqual(conteo.atendidos + conteo.pendientes, conteo.ingresados)

    def test_inconsistent_count_is_rejected(self):
        with self.assertRaises(ValueError):
            ConteoNivel(ingresados=3, atendidos=1, pendientes=1)
        with self.assertRaises(ValueError):
            ConteoNivel(ingresados=1, atendidos=2, pendientes=-1)

    def test_duplicate_client_ids_are_rejected(self):
        a = Cliente(id_llegada=1, nivel=Nivel.GENERAL, t_llegada=0.0)
        b = Cliente(id_llegada=1, nivel=Nivel.PREFERENCIAL, t_llegada=0.1)
        with self.assertRaises(ValueError):
            contar_por_nivel([a, b])


class ResultadoCorridaTests(unittest.TestCase):
    def test_run_result_contract(self):
        clientes, eventos = _corrida_ejemplo()
        parametros = _parametros()
        resultado = ResultadoCorrida(
            parametros=parametros, semilla=42, disciplina=Disciplina.PRIORIDAD,
            clientes=clientes, eventos=eventos, metricas={"utilizacion": 0.5},
        )
        self.assertIs(resultado.parametros, parametros)
        self.assertIs(resultado.unidad, Unidad.MINUTO)
        self.assertEqual(resultado.semilla, 42)
        self.assertIsInstance(resultado.clientes, tuple)
        self.assertIsInstance(resultado.eventos, tuple)
        self.assertEqual(resultado.metricas["utilizacion"], 0.5)
        with self.assertRaises(TypeError):
            resultado.metricas["nueva"] = 1.0
        self.assertEqual(resultado.conteos[Nivel.GENERAL].pendientes, 1)
        self.assertEqual(resultado.conteos[Nivel.PREFERENCIAL].pendientes, 1)

    def test_run_result_rejects_invalid_inputs(self):
        clientes, eventos = _corrida_ejemplo()
        base = dict(parametros=_parametros(), semilla=1, disciplina=Disciplina.FCFS,
                    clientes=clientes, eventos=eventos, metricas={})
        casos = {
            "semilla": [None, -1, True],
            "disciplina": ["fcfs"],
            "parametros": [None],
            "eventos": [list(reversed(eventos)),
                        eventos + [Evento(instante=3.0, tipo=TipoEvento.LLEGADA,
                                          cliente_id=99)]],
            "clientes": [clientes + [Cliente(id_llegada=1, nivel=Nivel.GENERAL,
                                             t_llegada=2.0)]],
            "metricas": [{"x": "alto"}, {1: 0.5}],
        }
        for campo, valores in casos.items():
            for valor in valores:
                with self.subTest(campo=campo, valor=valor):
                    with self.assertRaises((ValueError, TypeError)):
                        ResultadoCorrida(**{**base, campo: valor})


if __name__ == "__main__":
    unittest.main()
