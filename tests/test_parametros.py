"""Validation rules of scenario parameters (task A1, issue #1).

Horizon, warm-up and p values used here are test inputs, not documented
study requirements.
"""

import math
import unittest
from dataclasses import FrozenInstanceError

from src.modelo.parametros import (
    ADAMS_YEBOAH,
    MARHAMAH,
    ParametrosEscenario,
    Unidad,
    convertir_tasa,
    convertir_tiempo,
    crear_escenario,
    descomponer_llegadas,
    escenarios_familia,
    familia_adams_yeboah,
    familia_marhamah,
)

ORIGEN = "supuesto de prueba"


def _validos(**cambios):
    datos = dict(
        nombre="prueba", unidad=Unidad.MINUTO, lam=1.0, mu=2.0, c=1,
        p=0.25, origen_p=ORIGEN, horizon=100.0, warmup=10.0,
    )
    datos.update(cambios)
    return datos


class FamiliasDocumentadasTests(unittest.TestCase):
    def test_adams_yeboah_values_in_hours(self):
        self.assertEqual(ADAMS_YEBOAH.lam, 45.0)
        self.assertEqual(ADAMS_YEBOAH.mu, 12.0)
        self.assertIs(ADAMS_YEBOAH.unidad, Unidad.HORA)
        self.assertEqual(ADAMS_YEBOAH.capacidades, (8, 9, 10, 11, 12))

    def test_marhamah_values_in_minutes(self):
        self.assertEqual(MARHAMAH.lam, 0.3246)
        self.assertEqual(MARHAMAH.mu, 0.2839)
        self.assertIs(MARHAMAH.unidad, Unidad.MINUTO)
        self.assertEqual(MARHAMAH.capacidades, (2, 3, 4, 5))

    def test_scenario_keeps_family_rates_and_unit(self):
        adams = familia_adams_yeboah(10, 0.2, origen_p=ORIGEN, horizon=8.0, warmup=1.0)
        self.assertEqual((adams.lam, adams.mu, adams.c), (45.0, 12.0, 10))
        self.assertIs(adams.unidad, Unidad.HORA)
        self.assertEqual(adams.familia, ADAMS_YEBOAH.nombre)
        marh = familia_marhamah(3, 0.2, origen_p=ORIGEN, horizon=480.0, warmup=60.0)
        self.assertEqual((marh.lam, marh.mu, marh.c), (0.3246, 0.2839, 3))
        self.assertIs(marh.unidad, Unidad.MINUTO)
        self.assertEqual(marh.familia, MARHAMAH.nombre)

    def test_capacity_outside_documented_range_is_rejected(self):
        for familia, c in ((familia_adams_yeboah, 7), (familia_adams_yeboah, 13),
                           (familia_marhamah, 1), (familia_marhamah, 6)):
            with self.subTest(familia=familia.__name__, c=c):
                with self.assertRaises(ValueError):
                    familia(c, 0.2, origen_p=ORIGEN, horizon=10.0, warmup=0.0)

    def test_family_sweep_covers_every_capacity(self):
        escenarios = escenarios_familia(
            MARHAMAH, p=0.1, origen_p=ORIGEN, horizon=100.0, warmup=0.0,
        )
        self.assertEqual([e.c for e in escenarios], [2, 3, 4, 5])
        self.assertEqual(len({e.nombre for e in escenarios}), 4)

    def test_p_and_its_origin_are_required(self):
        with self.assertRaises(TypeError):
            familia_marhamah(2, origen_p=ORIGEN, horizon=10.0, warmup=0.0)
        with self.assertRaises(TypeError):
            familia_marhamah(2, 0.2, horizon=10.0, warmup=0.0)
        for origen in ("", "   ", None):
            with self.subTest(origen=origen), self.assertRaises(ValueError):
                ParametrosEscenario(**_validos(origen_p=origen))

    def test_waiting_criteria_default_to_pending(self):
        esc = familia_marhamah(2, 0.2, origen_p=ORIGEN, horizon=10.0, warmup=0.0)
        self.assertIsNone(esc.tau_p)
        self.assertIsNone(esc.tau_g)
        self.assertIsNone(esc.replicas)
        self.assertFalse(esc.criterios_espera_definidos)


class DescomposicionTests(unittest.TestCase):
    def test_level_rates_add_up_to_total(self):
        for p in (0.0, 0.137, 0.5, 1.0):
            with self.subTest(p=p):
                esc = familia_adams_yeboah(8, p, origen_p=ORIGEN, horizon=8.0, warmup=0.0)
                self.assertAlmostEqual(esc.lam_p, p * 45.0)
                self.assertAlmostEqual(esc.lam_g, (1 - p) * 45.0)
                self.assertTrue(math.isclose(esc.lam_p + esc.lam_g, esc.lam))

    def test_descomponer_llegadas(self):
        lam_p, lam_g = descomponer_llegadas(0.3246, 0.3)
        self.assertAlmostEqual(lam_p, 0.09738)
        self.assertTrue(math.isclose(lam_p + lam_g, 0.3246))


class EstabilidadTests(unittest.TestCase):
    def test_rho_adams_yeboah(self):
        esc = familia_adams_yeboah(8, 0.2, origen_p=ORIGEN, horizon=8.0, warmup=0.0)
        self.assertAlmostEqual(esc.carga_ofrecida, 3.75)
        self.assertAlmostEqual(esc.rho, 45.0 / 96.0)
        self.assertTrue(esc.es_estable)

    def test_rho_marhamah_smallest_capacity_is_stable(self):
        esc = familia_marhamah(2, 0.2, origen_p=ORIGEN, horizon=10.0, warmup=0.0)
        self.assertAlmostEqual(esc.rho, 0.3246 / (2 * 0.2839))
        self.assertAlmostEqual(esc.rho, 0.5717, places=4)
        self.assertTrue(esc.es_estable)
        esc.exigir_estabilidad()

    def test_unstable_scenario_is_allowed_but_flagged(self):
        esc = ParametrosEscenario(**_validos(lam=0.3246, mu=0.2839, c=1))
        self.assertGreater(esc.rho, 1.0)
        self.assertFalse(esc.es_estable)
        with self.assertRaises(ValueError):
            esc.exigir_estabilidad()

    def test_rho_equal_to_one_is_unstable(self):
        esc = ParametrosEscenario(**_validos(lam=2.0, mu=1.0, c=2))
        self.assertFalse(esc.es_estable)


class ConversionTests(unittest.TestCase):
    def test_rate_and_time_conversion(self):
        self.assertAlmostEqual(convertir_tasa(45.0, Unidad.HORA, Unidad.MINUTO), 0.75)
        self.assertAlmostEqual(convertir_tasa(0.75, Unidad.MINUTO, Unidad.HORA), 45.0)
        self.assertAlmostEqual(convertir_tiempo(2.0, Unidad.HORA, Unidad.MINUTO), 120.0)
        self.assertEqual(convertir_tasa(3.0, Unidad.HORA, Unidad.HORA), 3.0)

    def test_scenario_explicit_conversion_preserves_rho(self):
        esc = familia_adams_yeboah(
            9, 0.2, origen_p=ORIGEN, horizon=8.0, warmup=1.0, tau_p=0.1,
            tau_g=0.25, origen_tau=ORIGEN,
        )
        conv = esc.en_unidad(Unidad.MINUTO)
        self.assertIs(conv.unidad, Unidad.MINUTO)
        self.assertAlmostEqual(conv.lam, 0.75)
        self.assertAlmostEqual(conv.mu, 0.2)
        self.assertAlmostEqual(conv.horizon, 480.0)
        self.assertAlmostEqual(conv.warmup, 60.0)
        self.assertAlmostEqual(conv.tau_p, 6.0)
        self.assertAlmostEqual(conv.tau_g, 15.0)
        self.assertAlmostEqual(conv.rho, esc.rho)
        self.assertIs(esc.unidad, Unidad.HORA)

    def test_parameters_are_immutable(self):
        esc = ParametrosEscenario(**_validos())
        with self.assertRaises(FrozenInstanceError):
            esc.lam = 2.0


class RechazoTests(unittest.TestCase):
    def assertRechaza(self, **cambios):
        with self.assertRaises((ValueError, TypeError)):
            ParametrosEscenario(**_validos(**cambios))

    def test_valid_baseline_is_accepted(self):
        ParametrosEscenario(**_validos())
        ParametrosEscenario(**_validos(warmup=0.0, replicas=30, seed=7))

    def test_rates_must_be_positive_finite_numbers(self):
        for campo in ("lam", "mu"):
            for valor in (0.0, -1.0, math.inf, math.nan, True, "1"):
                with self.subTest(campo=campo, valor=valor):
                    self.assertRechaza(**{campo: valor})

    def test_tellers_must_be_positive_integer(self):
        for valor in (0, -1, 2.0, 1.5, True, "2"):
            with self.subTest(c=valor):
                self.assertRechaza(c=valor)

    def test_p_must_be_in_unit_interval(self):
        for valor in (-0.01, 1.01, math.nan, True, None):
            with self.subTest(p=valor):
                self.assertRechaza(p=valor)

    def test_horizon_must_exceed_non_negative_warmup(self):
        self.assertRechaza(horizon=10.0, warmup=10.0)
        self.assertRechaza(horizon=10.0, warmup=20.0)
        self.assertRechaza(warmup=-1.0)
        self.assertRechaza(horizon=math.inf)

    def test_replicas_must_be_positive_integer(self):
        for valor in (0, -3, 2.0, True):
            with self.subTest(replicas=valor):
                self.assertRechaza(replicas=valor)

    def test_seed_must_be_non_negative_integer(self):
        for valor in (-1, 1.0, True):
            with self.subTest(seed=valor):
                self.assertRechaza(seed=valor)

    def test_unit_and_name_are_required(self):
        self.assertRechaza(unidad="minuto")
        self.assertRechaza(nombre="")

    def test_waiting_criteria_need_positive_values_and_origin(self):
        self.assertRechaza(tau_p=5.0)
        self.assertRechaza(tau_p=0.0, origen_tau=ORIGEN)
        self.assertRechaza(tau_g=-1.0, origen_tau=ORIGEN)
        esc = ParametrosEscenario(**_validos(tau_p=5.0, origen_tau=ORIGEN))
        self.assertFalse(esc.criterios_espera_definidos)
        esc = ParametrosEscenario(**_validos(tau_p=5.0, tau_g=9.0, origen_tau=ORIGEN))
        self.assertTrue(esc.criterios_espera_definidos)


if __name__ == "__main__":
    unittest.main()
