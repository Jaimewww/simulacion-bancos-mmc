"""Pruebas deterministas del estado de colas compartidas (B1, issue #2)."""

import unittest

from src.modelo.cliente import Cliente, EstadoCliente, Nivel
from src.modelo.resultados import Disciplina
from src.modelo.sistema import Sistema


def cliente(numero: int, nivel: Nivel, llegada: float) -> Cliente:
    return Cliente(id_llegada=numero, nivel=nivel, t_llegada=llegada)


class ValidacionSistemaTests(unittest.TestCase):
    def test_rechaza_configuracion_invalida(self):
        for c in (0, -1, 1.0, True):
            with self.subTest(c=c), self.assertRaises(ValueError):
                Sistema(c)
        with self.assertRaises(ValueError):
            Sistema(1, "prioridad")

    def test_no_registra_dos_veces_al_mismo_cliente(self):
        sistema = Sistema(1)
        sistema.recibir(cliente(1, Nivel.GENERAL, 0.0), 0.0)
        with self.assertRaises(ValueError):
            sistema.recibir(cliente(1, Nivel.PREFERENCIAL, 1.0), 1.0)

    def test_error_de_inicio_no_deja_registro_parcial(self):
        sistema = Sistema(1)
        actual = cliente(1, Nivel.GENERAL, 2.0)
        with self.assertRaises(ValueError):
            sistema.recibir(actual, 1.0)
        self.assertTrue(sistema.hay_cajero_libre())
        self.assertEqual(sistema.recibir(actual, 2.0), 0)


class CajerosCompartidosTests(unittest.TestCase):
    def test_llegada_usa_cajero_libre_y_luego_espera(self):
        sistema = Sistema(2)
        clientes = [
            cliente(1, Nivel.GENERAL, 0.0),
            cliente(2, Nivel.PREFERENCIAL, 0.1),
            cliente(3, Nivel.GENERAL, 0.2),
        ]
        self.assertEqual(sistema.recibir(clientes[0], 0.0), 0)
        self.assertEqual(sistema.recibir(clientes[1], 0.1), 1)
        self.assertIsNone(sistema.recibir(clientes[2], 0.2))
        self.assertEqual(sistema.longitud_colas(), (0, 1))
        self.assertEqual(sistema.utilizacion_instantanea(), 1.0)

    def test_preferencial_no_interrumpe_servicio(self):
        sistema = Sistema(1, Disciplina.PRIORIDAD)
        general = cliente(1, Nivel.GENERAL, 0.0)
        preferencial = cliente(2, Nivel.PREFERENCIAL, 1.0)
        sistema.recibir(general, 0.0)
        sistema.recibir(preferencial, 1.0)
        self.assertIs(general.estado, EstadoCliente.EN_SERVICIO)
        self.assertIs(preferencial.estado, EstadoCliente.EN_COLA)
        self.assertIs(sistema.ocupados[0], general)

    def test_al_liberar_preferencial_pasa_antes_que_general(self):
        sistema = Sistema(1, Disciplina.PRIORIDAD)
        atendido = cliente(1, Nivel.GENERAL, 0.0)
        general = cliente(2, Nivel.GENERAL, 1.0)
        preferencial = cliente(3, Nivel.PREFERENCIAL, 2.0)
        sistema.recibir(atendido, 0.0)
        sistema.recibir(general, 1.0)
        sistema.recibir(preferencial, 2.0)
        siguiente = sistema.finalizar_servicio(atendido, 3.0)
        self.assertIs(siguiente, preferencial)
        self.assertEqual(preferencial.t_inicio_servicio, 3.0)
        self.assertEqual(sistema.longitud_colas(), (0, 1))
        self.assertFalse(sistema.hay_cajero_libre())

    def test_mismo_nivel_conserva_fcfs(self):
        sistema = Sistema(1, Disciplina.PRIORIDAD)
        atendido = cliente(1, Nivel.GENERAL, 0.0)
        primero = cliente(2, Nivel.PREFERENCIAL, 1.0)
        segundo = cliente(3, Nivel.PREFERENCIAL, 1.0)
        sistema.recibir(atendido, 0.0)
        sistema.recibir(primero, 1.0)
        sistema.recibir(segundo, 1.0)
        self.assertIs(sistema.finalizar_servicio(atendido, 2.0), primero)
        self.assertIs(sistema.finalizar_servicio(primero, 3.0), segundo)

    def test_fcfs_global_ignora_nivel(self):
        sistema = Sistema(1, Disciplina.FCFS)
        atendido = cliente(1, Nivel.GENERAL, 0.0)
        general = cliente(2, Nivel.GENERAL, 1.0)
        preferencial = cliente(3, Nivel.PREFERENCIAL, 2.0)
        sistema.recibir(atendido, 0.0)
        sistema.recibir(general, 1.0)
        sistema.recibir(preferencial, 2.0)
        self.assertIs(sistema.finalizar_servicio(atendido, 3.0), general)
        self.assertIs(sistema.finalizar_servicio(general, 4.0), preferencial)

    def test_no_queda_cajero_libre_mientras_hay_espera(self):
        sistema = Sistema(2)
        en_servicio = [cliente(1, Nivel.GENERAL, 0.0), cliente(2, Nivel.GENERAL, 0.1)]
        esperan = [cliente(3, Nivel.GENERAL, 0.2), cliente(4, Nivel.PREFERENCIAL, 0.3)]
        for actual in en_servicio + esperan:
            sistema.recibir(actual, actual.t_llegada)
        self.assertIs(sistema.finalizar_servicio(en_servicio[0], 1.0), esperan[1])
        self.assertEqual(sistema.cantidad_ocupados, 2)
        self.assertFalse(sistema.hay_cajero_libre())


if __name__ == "__main__":
    unittest.main()
