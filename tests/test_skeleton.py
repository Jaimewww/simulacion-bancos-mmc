"""Structural smoke checks only: no claim that DES behavior is implemented."""

import importlib
import subprocess
import sys
import unittest
import tempfile
from pathlib import Path

from src.modelo.cliente import Nivel
from src.modelo.resultados import Disciplina

ROOT = Path(__file__).resolve().parents[1]


class ScaffoldTests(unittest.TestCase):
    def test_priority_levels(self):
        self.assertLess(Nivel.PREFERENCIAL, Nivel.GENERAL)

    def test_disciplines(self):
        self.assertEqual({d.value for d in Disciplina}, {"fcfs", "prioridad"})

    def test_imports(self):
        for name in (
            "modelo.parametros", "modelo.cliente", "modelo.sistema",
            "modelo.motor_des", "modelo.analitico", "modelo.metricas",
            "modelo.resultados", "control.experimentos", "vista.animacion",
            "vista.graficas",
        ):
            with self.subTest(module=name):
                module = importlib.import_module(f"src.{name}")
                self.assertTrue(module.__doc__)

    def test_entry_point_reports_scaffold(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = subprocess.run(
                [sys.executable, str(ROOT / "main.py"), "--familia", "marhamah", "--replicas", "1", "--horizon", "10", "--warmup", "1", "--salida", tmp],
                capture_output=True, text=True, check=False,
                cwd=str(ROOT),
            )
        self.assertEqual(run.returncode, 0)
        self.assertIn("Inicio experimentos", run.stdout)


if __name__ == "__main__":
    unittest.main()
