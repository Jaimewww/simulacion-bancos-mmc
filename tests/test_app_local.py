import unittest
from src.modelo.resultados import Disciplina, ResultadoCorrida
from src.vista.app_local import (ConfiguracionVista, crear_parametros,
                                 ejecutar_simulacion, resumen_capacidad,
                                 serie_ocupacion)

def config(**changes):
    base=dict(llegadas_hora=18, servicios_hora=12, cajeros=3,
              proporcion_preferencial=.3, horizonte_minutos=60, semilla=123,
              disciplina=Disciplina.PRIORIDAD)
    return ConfiguracionVista(**{**base, **changes})

class VistaLocalTests(unittest.TestCase):
    def test_convierte_tasas_a_minutos(self):
        p=crear_parametros(config()); self.assertAlmostEqual(p.lam,18/60); self.assertAlmostEqual(p.mu,12/60)
    def test_admite_limites_ampliados(self):
        p=crear_parametros(config(llegadas_hora=1000,cajeros=24)); self.assertEqual(p.c,24); self.assertAlmostEqual(p.lam,1000/60)
    def test_rechaza_fuera_de_limites(self):
        for change in ({"llegadas_hora":0},{"llegadas_hora":1001},{"cajeros":0},{"cajeros":25}):
            with self.subTest(change=change),self.assertRaises(ValueError): crear_parametros(config(**change))
    def test_usa_motor_real_y_es_reproducible(self):
        a,b=ejecutar_simulacion(config()),ejecutar_simulacion(config())
        self.assertIsInstance(a,ResultadoCorrida); self.assertEqual(a.eventos,b.eventos)

    def test_graficas_se_derivan_del_resultado_real(self):
        resultado=ejecutar_simulacion(config())
        tiempos,ocupados=serie_ocupacion(resultado)
        datos=resumen_capacidad(resultado)
        self.assertEqual((tiempos[0],tiempos[-1]),(0.0,resultado.parametros.horizon))
        self.assertTrue(all(0 <= valor <= resultado.parametros.c for valor in ocupados))
        self.assertAlmostEqual(datos["rho"],resultado.parametros.rho)
        self.assertAlmostEqual(datos["utilizacion"],resultado.metricas["utilizacion"])

if __name__ == "__main__": unittest.main()
