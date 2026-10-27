"""Pruebas D2 del tablero: reconstrucción de una corrida real y captura estática.

La carga es determinista y preasignada (interfaz pública del motor B2): el
tablero solo reconstruye los eventos ya registrados, no simula ni sortea.
"""

import copy
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, cast

import matplotlib.pyplot as plt

from src.modelo.motor_des import LlegadaPlaneada, MotorDES
from src.modelo.cliente import Nivel
from src.modelo.parametros import ParametrosEscenario, Unidad
from src.modelo.resultados import Disciplina, TipoEvento
from src.vista import animacion
from src.vista.graficas import textos_figura

ROOT = Path(__file__).resolve().parents[1]

# c=1: 0 ocupa el cajero; 1 y 5 esperan en general; 2 espera en preferencial;
# 3 llega justo cuando 0 termina (4.0) y encuentra el cajero reasignado.
CARGA = (
    LlegadaPlaneada(0, 0.0, Nivel.GENERAL, 4.0),
    LlegadaPlaneada(1, 1.0, Nivel.GENERAL, 2.0),
    LlegadaPlaneada(5, 1.5, Nivel.GENERAL, 1.0),
    LlegadaPlaneada(2, 2.0, Nivel.PREFERENCIAL, 1.0),
    LlegadaPlaneada(3, 4.0, Nivel.PREFERENCIAL, 2.0),
    LlegadaPlaneada(4, 5.0, Nivel.GENERAL, 1.0),
)


def parametros(*, c=1, horizon=12.0, warmup=0.0, seed=123):
    return ParametrosEscenario(
        nombre="sintetico-d2", unidad=Unidad.MINUTO, lam=1.0, mu=1.0, c=c,
        p=0.4, origen_p="supuesto sintético de prueba", horizon=horizon,
        warmup=warmup, seed=seed,
    )


def corrida(disciplina=Disciplina.PRIORIDAD, **kwargs):
    return MotorDES(parametros(**kwargs), disciplina, carga=CARGA).correr()


def firma(resultado):
    """Huella de todo lo que el tablero no debe tocar."""
    clientes = tuple(
        (c.id_llegada, c.nivel, c.t_llegada, c.t_inicio_servicio,
         c.t_fin_servicio, c.cajero, c.condiciones)
        for c in resultado.clientes
    )
    return clientes, resultado.eventos, dict(resultado.metricas)


class ReconstruccionTests(unittest.TestCase):
    def test_cajero_ocupado_y_colas_ordenadas_antes_de_la_salida(self):
        estado = animacion.reconstruir_tablero(corrida(), 3.5)
        self.assertEqual(estado.cajeros, (0,))
        self.assertEqual(estado.cola_preferencial, (2,))
        self.assertEqual(estado.cola_general, (1, 5))  # FIFO dentro del nivel
        self.assertEqual((estado.instante, estado.unidad), (3.5, "minuto"))

    def test_llegada_simultanea_con_la_salida_espera_su_turno(self):
        estado = animacion.reconstruir_tablero(corrida(), 4.0)
        # El fin de servicio (0) se procesa antes que la llegada (3): el cajero
        # pasa a 2 por prioridad y 3 queda esperando desde ese mismo instante.
        self.assertEqual(estado.cajeros, (2,))
        self.assertEqual(estado.cola_preferencial, (3,))
        self.assertEqual(estado.cola_general, (1, 5))

    def test_prioridad_y_fcfs_difieren_con_los_mismos_eventos(self):
        prioridad = animacion.reconstruir_tablero(corrida(), 5.5)
        fcfs = animacion.reconstruir_tablero(corrida(Disciplina.FCFS), 5.5)
        self.assertEqual(prioridad.cajeros, (3,))
        self.assertEqual(prioridad.cola_preferencial, ())
        self.assertEqual(prioridad.cola_general, (1, 5, 4))
        self.assertEqual(fcfs.cajeros, (1,))
        self.assertEqual(fcfs.cola_preferencial, (2, 3))
        self.assertEqual(fcfs.cola_general, (5, 4))
        self.assertIs(prioridad.disciplina, Disciplina.PRIORIDAD)

    def test_cajeros_ocupados_y_libres_se_distinguen(self):
        estado = animacion.reconstruir_tablero(corrida(c=2), 2.5)
        self.assertEqual(estado.cajeros, (0, 1))
        self.assertEqual(estado.cola_preferencial, (2,))
        self.assertEqual(estado.cola_general, (5,))
        libre = animacion.reconstruir_tablero(corrida(c=2), 0.5)
        self.assertEqual(libre.cajeros, (0, None))  # None = libre, nunca 0
        self.assertEqual((libre.cola_preferencial, libre.cola_general), ((), ()))

    def test_estado_vacio_en_el_horizonte(self):
        estado = animacion.reconstruir_tablero(corrida(), 12.0)
        self.assertEqual(estado.cajeros, (None,))
        self.assertEqual((estado.cola_preferencial, estado.cola_general), ((), ()))

    def test_rechaza_instante_invalido_o_fuera_de_ventana(self):
        resultado = corrida()
        for instante in (-1.0, float("nan"), float("inf"), 12.5, True, "3"):
            with self.subTest(instante=instante):
                with self.assertRaises(ValueError):
                    animacion.reconstruir_tablero(resultado, instante)
        with self.assertRaises(TypeError):
            animacion.reconstruir_tablero(cast(Any, {"eventos": ()}), 0.0)

    def test_none_de_tau_se_conserva_y_no_inventa_demografia(self):
        estado = animacion.reconstruir_tablero(corrida(), 3.5)
        self.assertIsNone(estado.tau_p)
        self.assertIsNone(estado.tau_g)
        self.assertEqual(estado.origen_p, "supuesto sintético de prueba")


class DibujoTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(plt.close, "all")

    def test_no_muta_la_corrida(self):
        resultado = corrida()
        antes = copy.deepcopy(firma(resultado))
        estado = animacion.reconstruir_tablero(resultado, 5.5)
        animacion.dibujar_tablero(estado)
        self.assertEqual(firma(resultado), antes)

    def test_figura_rotula_unidad_cajeros_colas_y_supuestos(self):
        fig = animacion.dibujar_tablero(animacion.reconstruir_tablero(corrida(), 3.5))
        textos = " ".join(textos_figura(fig))
        for esperado in ("minuto", "t = 3.5", "Cajero 0", "cliente 0",
                         "Cola preferencial (n=1)", "P2", "Cola general (n=2)",
                         "G1 → G5", "prioridad", "sintetico-d2", "semilla: 123",
                         "p=0.4", "supuesto sintético de prueba",
                         "τp=no definido", "τg=no definido", "no simula"):
            self.assertIn(esperado, textos)
        leyenda_obj = fig.get_axes()[0].get_legend()
        assert leyenda_obj is not None
        leyenda = " ".join(t.get_text() for t in leyenda_obj.get_texts())
        for esperado in ("ocupado", "libre", "preferencial", "general"):
            self.assertIn(esperado, leyenda.lower())

    def test_figura_con_colas_vacias(self):
        fig = animacion.dibujar_tablero(animacion.reconstruir_tablero(corrida(), 12.0))
        textos = " ".join(textos_figura(fig))
        self.assertIn("Cola preferencial (n=0)", textos)
        self.assertIn("Cola general (n=0)", textos)
        self.assertIn("(vacía)", textos)
        self.assertIn("Cajero 0", textos)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(plt.close, "all")
        self.salida = Path(self.tmp.name) / "tablero.png"

    def cli(self, *args):
        entorno = dict(os.environ, MPLBACKEND="Agg")
        entorno.pop("PYTHONPATH", None)
        return subprocess.run([sys.executable, "-m", "src.control.tablero", *args],
                              cwd=ROOT, env=entorno, capture_output=True, text=True)

    def argumentos(self, *extra):
        return ["--familia", "marhamah", "--c", "3", "--p", "0.3",
                "--origen-p", "supuesto de prueba", "--horizon", "480",
                "--warmup", "60", "--semilla", "7", *extra]

    def test_cli_ayuda_documenta_argumentos(self):
        r = self.cli("--help")
        self.assertEqual(r.returncode, 0, r.stderr)
        for texto in ("--familia", "--c", "--p", "--origen-p", "--horizon",
                      "--warmup", "--semilla", "--disciplina", "--instante", "--salida"):
            self.assertIn(texto, r.stdout)

    def test_cli_guarda_un_png_de_una_corrida_real(self):
        r = self.cli(*self.argumentos("--salida", str(self.salida)))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stderr, "")
        self.assertTrue(self.salida.is_file())
        self.assertEqual(self.salida.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        resultado = MotorDES(parametros_real(), Disciplina.PRIORIDAD, semilla=7).correr()
        estado = animacion.reconstruir_tablero(resultado, 480.0)
        cajeros = ", ".join("libre" if c is None else f"cliente {c}" for c in estado.cajeros)
        self.assertEqual(r.stdout, (
            "Tablero D2: instante 480 minuto (horizonte)\n"
            "Corrida: marhamah|c=3 · semilla 7 · disciplina prioridad · p=0.3 · "
            "origen_p=supuesto de prueba\n"
            f"Cajeros (3): {cajeros}\n"
            f"Esperando: preferencial {len(estado.cola_preferencial)}, "
            f"general {len(estado.cola_general)}\n"
            f"PNG: {self.salida}\n"))

    def test_cli_rechaza_instante_y_configuracion_sin_escribir(self):
        casos = {
            "instante fuera de ventana": self.argumentos(
                "--instante", "481", "--salida", str(self.salida)),
            "instante negativo": self.argumentos(
                "--instante", "-1", "--salida", str(self.salida)),
            "capacidad fuera de familia": ["--familia", "marhamah", "--c", "99",
                                           "--p", "0.3", "--origen-p", "supuesto",
                                           "--horizon", "480", "--warmup", "60",
                                           "--salida", str(self.salida)],
            "p inválido": ["--familia", "marhamah", "--c", "3", "--p", "1.5",
                           "--origen-p", "supuesto", "--horizon", "480",
                           "--warmup", "60", "--salida", str(self.salida)],
            "falta --p": ["--familia", "marhamah", "--c", "3",
                          "--origen-p", "supuesto", "--horizon", "480",
                          "--warmup", "60", "--salida", str(self.salida)],
        }
        for nombre, argumentos in casos.items():
            with self.subTest(caso=nombre):
                r = self.cli(*argumentos)
                self.assertEqual(r.returncode, 2, r.stderr)
                self.assertEqual(r.stdout, "")
                self.assertIn("error:", r.stderr)
                self.assertNotIn("Traceback", r.stderr)
                self.assertFalse(self.salida.exists())


def parametros_real():
    from src.modelo.parametros import crear_escenario, MARHAMAH
    return crear_escenario(MARHAMAH, 3, 0.3, origen_p="supuesto de prueba",
                           horizon=480.0, warmup=60.0, seed=7)


if __name__ == "__main__":
    unittest.main()
