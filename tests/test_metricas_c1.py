"""C1 regression tests: warmup, metrics, pending clients and balances."""
import unittest
from dataclasses import replace

from src.modelo.cliente import Nivel
from src.modelo.parametros import ParametrosEscenario, Unidad
from src.modelo.resultados import Disciplina
from src.modelo.motor_des import MotorDES, LlegadaPlaneada
from src.modelo.metricas import calcular_metricas_observadas, comprobacion_little, conservacion_clientes


def escenario(**kw):
    valores = dict(nombre='prueba', unidad=Unidad.HORA, lam=1, mu=2, c=1,
                   p=0.5, origen_p='supuesto de prueba', horizon=10, warmup=2)
    return ParametrosEscenario(**(valores | kw))


def corrida():
    carga = tuple(LlegadaPlaneada(i, t, Nivel.GENERAL, s) for i, (t, s) in
                  enumerate(((0, 3), (1, 1), (2, 1), (3, 10), (4, 1))))
    return MotorDES(escenario(), Disciplina.FCFS, semilla=1, carga=carga).correr()


class MetricasTests(unittest.TestCase):
    def test_cohorte_pendientes_y_medias(self):
        obs = calcular_metricas_observadas(corrida())
        # Post-warmup: waits 2,2 and one censored; only first completed (W=3).
        self.assertEqual(obs['Wq_global_muestra'], 2)
        self.assertEqual(obs['n_muestra_inicio_global'], 2)
        self.assertEqual(obs['W_sistema_por_nivel_muestra_completa']['GENERAL']['W_prom_muestra'], 3)
        self.assertIsNone(obs['Wq_por_nivel_muestra_inicio']['PREFERENCIAL']['Wq_prom_muestra'])
        self.assertEqual(obs['conteos_por_nivel']['GENERAL']['en_cola'], 1)
        self.assertEqual(obs['conteos_por_nivel']['GENERAL']['en_servicio'], 1)
        # Includes carry-in and final censored wait: area 1+2+2+6=11.
        self.assertEqual(obs['Lq_temporal']['global'], 11/8)

    def test_little_and_conservation_executed(self):
        run = corrida()
        self.assertTrue(conservacion_clientes(run)['conservacion_ok'])
        checks = comprobacion_little(run)['comprobaciones_little']
        self.assertTrue(all(c['identidad_ok'] for c in checks))
        self.assertEqual(checks[-1]['lambda_Wq'], 3/8*2)
        self.assertFalse(checks[-1]['dentro_tol'])
        self.assertFalse(conservacion_clientes(replace(run, eventos=()))['conservacion_ok'])
        broken = replace(run, metricas=dict(run.metricas) | {'lq_global': 100})
        self.assertFalse(comprobacion_little(broken)['comprobaciones_little'][-1]['identidad_ok'])

    def test_global_wait_is_customer_weighted(self):
        p = escenario(warmup=0)
        carga = (LlegadaPlaneada(0,0,Nivel.GENERAL,3),
                 LlegadaPlaneada(1,1,Nivel.GENERAL,1),
                 LlegadaPlaneada(2,2,Nivel.PREFERENCIAL,1))
        run = MotorDES(p, Disciplina.FCFS, semilla=1, carga=carga).correr()
        self.assertAlmostEqual(calcular_metricas_observadas(run)['Wq_global_muestra'], 4/3)


if __name__ == '__main__':
    unittest.main()
