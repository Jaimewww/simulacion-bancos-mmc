import unittest

from src.modelo.analitico import prob_vacio, prob_espera, lq, wq, l_sistema, w_sistema, erlang_c_desde_parametros
from src.modelo.parametros import familia_marhamah


class AnaliticoC1Tests(unittest.TestCase):
    def test_mm1_lambda1_mu2(self):
        lam, mu, c = 1.0, 2.0, 1
        self.assertAlmostEqual(lam/(c*mu), 0.5, places=12)
        self.assertAlmostEqual(lq(lam, mu, c), 0.5, places=12)
        self.assertAlmostEqual(wq(lam, mu, c), 0.5, places=12)
        self.assertAlmostEqual(l_sistema(lam, mu, c), 1.0, places=12)
        self.assertAlmostEqual(w_sistema(lam, mu, c), 1.0, places=12)

    def test_rechaza_rho_ge_1(self):
        with self.assertRaises(ValueError):
            prob_espera(2.0, 1.0, 1)
        with self.assertRaises(ValueError):
            prob_espera(1.0, 1.0, 1)

    def test_erlang_c_desde_parametros(self):
        p = familia_marhamah(3, p=0.3, origen_p='supuesto', horizon=60.0, warmup=10.0)
        er = erlang_c_desde_parametros(p)
        self.assertIn('Lq', er)
        self.assertIn('Wq', er)
        self.assertIn('L', er)
        self.assertIn('W', er)
        self.assertGreaterEqual(er['rho'], 0)


if __name__ == '__main__':
    unittest.main()
