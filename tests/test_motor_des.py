"""Pruebas de calendario, reproducción y conservación del motor DES B2."""

import unittest

from src.modelo.cliente import EstadoCliente, Nivel
from src.modelo.motor_des import LlegadaPlaneada, MotorDES, generar_carga
from src.modelo.parametros import ParametrosEscenario, Unidad
from src.modelo.resultados import Disciplina, TipoEvento


def parametros(*, seed=123, horizon=5.0, warmup=0.0, c=1):
    return ParametrosEscenario(
        nombre="sintetico-b2", unidad=Unidad.MINUTO, lam=1.0, mu=1.0,
        c=c, p=0.4, origen_p="supuesto de prueba", horizon=horizon,
        warmup=warmup, seed=seed,
    )


def firma(resultado):
    clientes = tuple(
        (c.id_llegada, c.nivel, c.t_llegada, c.t_inicio_servicio,
         c.t_fin_servicio, c.cajero)
        for c in resultado.clientes
    )
    return clientes, resultado.eventos, dict(resultado.metricas)


class GeneracionTests(unittest.TestCase):
    def test_misma_semilla_genera_misma_carga(self):
        escenario = parametros()
        self.assertEqual(generar_carga(escenario, 77), generar_carga(escenario, 77))
        self.assertTrue(all(x.instante <= escenario.horizon
                            for x in generar_carga(escenario, 77)))

    def test_semilla_es_obligatoria_y_validada(self):
        sin_semilla = parametros(seed=None)
        with self.assertRaises(ValueError):
            MotorDES(sin_semilla)
        with self.assertRaises(ValueError):
            MotorDES(sin_semilla, semilla=-1)

    def test_carga_reutilizable_entre_disciplinas(self):
        escenario = parametros(c=2)
        carga = generar_carga(escenario, 99)
        prioridad = MotorDES(escenario, Disciplina.PRIORIDAD, carga=carga).carga
        fcfs = MotorDES(escenario, Disciplina.FCFS, carga=carga).carga
        self.assertEqual(prioridad, fcfs)


class EjecucionTests(unittest.TestCase):
    def setUp(self):
        self.escenario = parametros()
        self.carga = (
            LlegadaPlaneada(0, 0.0, Nivel.GENERAL, 4.0),
            LlegadaPlaneada(1, 1.0, Nivel.GENERAL, 1.0),
            LlegadaPlaneada(2, 2.0, Nivel.PREFERENCIAL, 1.0),
        )

    def test_prioridad_no_expropiativa_y_pendientes(self):
        resultado = MotorDES(self.escenario, carga=self.carga).correr()
        primero, general, preferencial = resultado.clientes
        self.assertEqual(primero.t_fin_servicio, 4.0)
        self.assertEqual(preferencial.t_inicio_servicio, 4.0)
        self.assertEqual(general.t_inicio_servicio, 5.0)
        self.assertIs(general.estado, EstadoCliente.EN_SERVICIO)
        self.assertEqual(resultado.conteos[Nivel.GENERAL].pendientes, 1)

    def test_areas_temporales_y_utilizacion(self):
        metricas = MotorDES(self.escenario, carga=self.carga).correr().metricas
        self.assertEqual(metricas["area_cola_general"], 4.0)
        self.assertEqual(metricas["area_cola_preferencial"], 2.0)
        self.assertEqual(metricas["area_ocupados"], 5.0)
        self.assertEqual(metricas["lq_global"], 1.2)
        self.assertEqual(metricas["utilizacion"], 1.0)

    def test_reproduccion_exacta(self):
        a = MotorDES(parametros(seed=42)).correr()
        b = MotorDES(parametros(seed=42)).correr()
        self.assertEqual(firma(a), firma(b))

    def test_conservacion_y_registro_cronologico(self):
        resultado = MotorDES(self.escenario, carga=self.carga).correr()
        for conteo in resultado.conteos.values():
            self.assertEqual(conteo.ingresados, conteo.atendidos + conteo.pendientes)
        instantes = [evento.instante for evento in resultado.eventos]
        self.assertEqual(instantes, sorted(instantes))
        self.assertTrue(all(instante <= self.escenario.horizon for instante in instantes))

    def test_fin_precede_inicio_en_el_mismo_instante(self):
        eventos = MotorDES(self.escenario, carga=self.carga).correr().eventos
        en_cuatro = [evento.tipo for evento in eventos if evento.instante == 4.0]
        self.assertEqual(en_cuatro, [TipoEvento.FIN_SERVICIO, TipoEvento.INICIO_SERVICIO])

    def test_calentamiento_recorta_integrales(self):
        escenario = parametros(warmup=2.0)
        metricas = MotorDES(escenario, carga=self.carga).correr().metricas
        self.assertEqual(metricas["ventana_medida"], 3.0)
        self.assertEqual(metricas["area_cola_general"], 3.0)
        self.assertEqual(metricas["area_cola_preferencial"], 2.0)
        self.assertEqual(metricas["area_ocupados"], 3.0)


if __name__ == "__main__":
    unittest.main()
