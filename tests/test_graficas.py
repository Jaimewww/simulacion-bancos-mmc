"""D1 view tests: figuras de espera, Erlang C y utilización/ociosidad.

Las filas son sintéticas y se construyen a mano con las mismas columnas que
exporta `main.py` en `resumen_*.csv`; se rotulan como datos sintéticos. La
vista no simula ni calcula métricas: solo dibuja lo exportado.
"""

import copy
import csv
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.container import ErrorbarContainer

from src.vista import graficas

ROOT = Path(__file__).resolve().parents[1]
METRICAS = ("Wq_pref", "Wq_gen", "Wq_global", "Lq_global", "utilizacion")
CAMPOS = (["familia_c", "disciplina", "n_replicas", "unidad", "p", "origen_p"]
          + [f"{m}_{s}" for m in METRICAS for s in ("media", "n", "ic95_inf", "ic95_sup")]
          + ["coherencia_json"])
SIN_VALOR = (None, None, None)


def fila(familia="marhamah", c=2, disciplina="fcfs", unidad="minuto", p=0.2, n=3,
         wq_pref=(0.5, 0.4, 0.6), wq_gen=(1.0, 0.8, 1.2), wq_global=(0.9, 0.7, 1.1),
         util=(0.6, 0.5, 0.7), teoricos=None):
    """Una fila de resumen con las columnas que consume la vista D1."""
    datos = {"familia_c": f"{familia}|c={c}", "disciplina": disciplina, "n_replicas": str(n),
             "unidad": unidad, "p": repr(float(p)), "origen_p": "supuesto sintético de prueba"}
    for nombre, valores in (("Wq_pref", wq_pref), ("Wq_gen", wq_gen), ("Wq_global", wq_global),
                            ("Lq_global", SIN_VALOR), ("utilizacion", util)):
        media, inf, sup = valores
        datos[f"{nombre}_media"] = "" if media is None else repr(float(media))
        datos[f"{nombre}_n"] = "0" if media is None else str(n)
        datos[f"{nombre}_ic95_inf"] = "" if inf is None else repr(float(inf))
        datos[f"{nombre}_ic95_sup"] = "" if sup is None else repr(float(sup))
    if teoricos is None:
        teoricos = {"Wq_global": 1.71, "Lq_global": 0.55, "utilizacion": 0.57}
    datos["coherencia_json"] = json.dumps(
        [{"tipo": "erlang_c", "metrica": k, "teorico": v} for k, v in teoricos.items()])
    return datos


def familia_sintetica(familia="marhamah", unidad="minuto", capacidades=(2, 3), n=3, teoricos=None):
    """Dos capacidades x dos disciplinas; valores distintos por capacidad."""
    filas = []
    for c in capacidades:
        for disciplina in ("fcfs", "prioridad"):
            filas.append(fila(familia=familia, c=c, disciplina=disciplina, unidad=unidad, n=n,
                              wq_pref=(0.1 * c, 0.05 * c, 0.15 * c),
                              wq_gen=(0.2 * c, 0.1 * c, 0.3 * c),
                              wq_global=(0.9 + 0.1 * c, 0.7 + 0.1 * c, 1.1 + 0.1 * c),
                              util=(0.6, 0.5, 0.7), teoricos=teoricos))
    return filas


def escribir_csv(ruta, filas):
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=CAMPOS)
        escritor.writeheader()
        escritor.writerows(filas)


def series_dibujadas(ax):
    """Etiquetas y valores Y realmente dibujados en los ejes."""
    series = {}
    for contenedor in ax.containers:
        if isinstance(contenedor, ErrorbarContainer):
            series[contenedor.get_label()] = list(contenedor.lines[0].get_ydata())
    for linea in ax.get_lines():
        if not linea.get_label().startswith("_"):
            series.setdefault(linea.get_label(), list(linea.get_ydata()))
    return series


def extremos_ic(ax, etiqueta):
    """Extremos (inferior, superior) dibujados como barras de IC de una serie."""
    for contenedor in ax.containers:
        if isinstance(contenedor, ErrorbarContainer) and contenedor.get_label() == etiqueta:
            (x0, y0), (x1, y1) = contenedor.lines[2][0].get_segments()[0]
            return (min(y0, y1), max(y0, y1))
    raise AssertionError(f"sin barras de IC para {etiqueta!r}")


class GraficasTests(unittest.TestCase):
    def assertSerie(self, obtenido, esperado):
        """Compara series dibujadas admitiendo redondeo de coma flotante."""
        self.assertEqual(len(obtenido), len(esperado))
        for valor, referencia in zip(obtenido, esperado, strict=True):
            if referencia is None:
                self.assertTrue(math.isnan(valor))
            else:
                self.assertAlmostEqual(valor, referencia, places=9)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(plt.close, "all")
        self.resumen = Path(self.tmp.name) / "resumen.csv"

    def leer(self, filas, ruta=None):
        destino = Path(ruta) if ruta else self.resumen
        escribir_csv(destino, filas)
        return graficas.cargar_resumen(destino)

    def test_conserva_metricas_faltantes_y_sin_ic_corto(self):
        filas = self.leer([fila(wq_pref=SIN_VALOR), fila(c=3, n=1)])
        pref = filas[0].intervalos["Wq_pref"]
        self.assertIsNone(pref.media)
        self.assertEqual(pref.n, 0)
        self.assertIsNone(pref.inf)
        self.assertIsNone(pref.sup)
        self.assertIsNone(filas[0].intervalos["Lq_global"].media)
        # n=1: se conserva la media pero no se fabrica un IC aunque el CSV traiga extremos.
        self.assertAlmostEqual(filas[1].intervalos["Wq_global"].media, 0.9)
        self.assertEqual(filas[1].intervalos["Wq_global"].n, 1)
        self.assertIsNone(filas[1].intervalos["Wq_global"].inf)
        self.assertEqual((filas[1].familia, filas[1].capacidad, filas[1].p), ("marhamah", 3, 0.2))
        self.assertEqual(filas[1].unidad, "minuto")

    def test_invertir_intervalo_gira_extremos(self):
        invertido = graficas.invertir_intervalo(graficas.Intervalo(0.6, 3, 0.5, 0.7))
        self.assertAlmostEqual(invertido.media, 0.4)
        self.assertAlmostEqual(invertido.inf, 0.3)  # 1 - 0.7
        self.assertAlmostEqual(invertido.sup, 0.5)  # 1 - 0.5
        self.assertEqual(invertido.n, 3)
        vacio = graficas.invertir_intervalo(graficas.Intervalo(None, 0, None, None))
        self.assertIsNone(vacio.media)
        self.assertIsNone(vacio.sup)
        sin_ic = graficas.invertir_intervalo(graficas.Intervalo(0.6, 1, None, None))
        self.assertAlmostEqual(sin_ic.media, 0.4)
        self.assertIsNone(sin_ic.inf)
        self.assertIsNone(sin_ic.sup)

    def test_serie_por_capacidad_ordena_y_marca_faltantes(self):
        serie = graficas.serie_por_capacidad(self.leer(familia_sintetica(capacidades=(3, 2))),
                                            "fcfs", "Wq_pref")
        self.assertEqual(list(serie.capacidades), [2, 3])
        self.assertSerie(serie.medias, [0.2, 0.3])
        self.assertSerie(serie.inf, [0.1, 0.15])
        self.assertSerie(serie.sup, [0.3, 0.45])
        parcial = graficas.serie_por_capacidad(
            self.leer([fila(c=2), fila(c=3, wq_pref=SIN_VALOR)]), "fcfs", "Wq_pref")
        self.assertAlmostEqual(parcial.medias[0], 0.5)
        self.assertTrue(math.isnan(parcial.medias[1]))
        self.assertTrue(math.isnan(parcial.inf[1]))
        duplicado = self.leer([fila(c=2), fila(c=2)], Path(self.tmp.name) / "duplicado.csv")
        with self.assertRaisesRegex(ValueError, "duplicada"):
            graficas.serie_por_capacidad(duplicado, "fcfs", "Wq_pref")

    def test_figura_wq_niveles_puntos_y_etiquetas(self):
        fig = graficas.figura_wq_por_nivel(self.leer(familia_sintetica()))
        textos = " ".join(graficas.textos_figura(fig))
        for esperado in ("marhamah", "Unidad: minuto", "p=0.2",
                         "supuesto sintético de prueba", "n=3", "IC95"):
            self.assertIn(esperado, textos)
        ax = fig.get_axes()[0]
        self.assertIn("minuto", ax.get_ylabel())
        self.assertIn("cajeros", ax.get_xlabel())
        self.assertEqual([t.get_text() for t in ax.get_legend().get_texts()],
                         ["FCFS · Wq preferencial (n=3)", "FCFS · Wq general (n=3)",
                          "Prioridad · Wq preferencial (n=3)", "Prioridad · Wq general (n=3)"])
        lineas = series_dibujadas(ax)
        self.assertSerie(lineas["FCFS · Wq preferencial (n=3)"], [0.2, 0.3])
        self.assertSerie(lineas["Prioridad · Wq general (n=3)"], [0.4, 0.6])
        bajo, alto = extremos_ic(ax, "FCFS · Wq general (n=3)")
        self.assertAlmostEqual(bajo, 0.2)
        self.assertAlmostEqual(alto, 0.6)

    def test_nivel_sin_muestra_no_se_dibuja_como_cero(self):
        fig = graficas.figura_wq_por_nivel(
            self.leer([fila(c=2, wq_pref=SIN_VALOR), fila(c=3, wq_pref=SIN_VALOR)]))
        ax = fig.get_axes()[0]
        dibujadas = series_dibujadas(ax)
        etiqueta = [e for e in dibujadas if e.startswith("FCFS · Wq preferencial")][0]
        self.assertIn("sin muestra", etiqueta)
        self.assertTrue(all(math.isnan(v) for v in dibujadas[etiqueta]))

    def test_figura_erlang_usa_solo_coherencia_json(self):
        fig = graficas.figura_wq_global_vs_erlang_c(self.leer(familia_sintetica(teoricos={"Wq_global": 9.25})))
        ax = fig.get_axes()[0]
        lineas = series_dibujadas(ax)
        self.assertSerie(lineas["Erlang C (teórico)"], [9.25, 9.25])
        self.assertSerie(lineas["FCFS · Wq global (n=3)"], [1.1, 1.2])
        self.assertIn("minuto", ax.get_ylabel())
        sin_teoricos = graficas.figura_wq_global_vs_erlang_c(self.leer(familia_sintetica(teoricos={})))
        textos = " ".join(graficas.textos_figura(sin_teoricos))
        self.assertIn("coherencia_json", textos)
        self.assertNotIn("Erlang C (teórico)", series_dibujadas(sin_teoricos.get_axes()[0]))

    def test_figura_utilizacion_ociosidad_ic_girado(self):
        fig = graficas.figura_utilizacion_ociosidad(self.leer(familia_sintetica()))
        ax = fig.get_axes()[0]
        self.assertIn("fracción", ax.get_ylabel())
        self.assertIn("utilizaci", " ".join(graficas.textos_figura(fig)).lower())
        lineas = series_dibujadas(ax)
        self.assertSerie(lineas["FCFS · utilización ρ (n=3)"], [0.6, 0.6])
        self.assertSerie(lineas["FCFS · ociosidad 1-ρ (n=3)"], [0.4, 0.4])
        for etiqueta, (bajo, alto) in (("FCFS · utilización ρ (n=3)", (0.5, 0.7)),
                                       ("FCFS · ociosidad 1-ρ (n=3)", (0.3, 0.5))):
            with self.subTest(etiqueta=etiqueta):
                obtenido = extremos_ic(ax, etiqueta)
                self.assertAlmostEqual(obtenido[0], bajo)
                self.assertAlmostEqual(obtenido[1], alto)

    def test_rotulo_datos_sinteticos(self):
        filas = self.leer(familia_sintetica())
        con = " ".join(graficas.textos_figura(graficas.figura_wq_por_nivel(filas, sintetico=True))).lower()
        sin = " ".join(graficas.textos_figura(graficas.figura_wq_por_nivel(filas))).lower()
        self.assertIn("datos sintéticos", con)
        self.assertNotIn("datos sintéticos", sin)
        for fig in graficas.generar_figuras(filas, sintetico=True).values():
            self.assertIn("datos sintéticos", " ".join(graficas.textos_figura(fig)).lower())

    def test_familias_y_unidades_separadas(self):
        filas = familia_sintetica("marhamah", "minuto") + familia_sintetica("adams_yeboah", "hora", (8,))
        figuras = graficas.generar_figuras(self.leer(filas))
        self.assertEqual(list(figuras), ["marhamah|wq_niveles", "marhamah|wq_global_erlang",
                                         "marhamah|utilizacion_ociosidad", "adams_yeboah|wq_niveles",
                                         "adams_yeboah|wq_global_erlang",
                                         "adams_yeboah|utilizacion_ociosidad"])
        self.assertIn("Unidad: hora", " ".join(graficas.textos_figura(figuras["adams_yeboah|wq_niveles"])))
        self.assertIn("Unidad: minuto",
                      " ".join(graficas.textos_figura(figuras["marhamah|utilizacion_ociosidad"])))
        mezcla = [fila(unidad="minuto"), fila(c=3, unidad="hora")]
        with self.assertRaisesRegex(ValueError, "unidad inconsistente"):
            graficas.generar_figuras(self.leer(mezcla, Path(self.tmp.name) / "mixto.csv"))

    def test_nombres_de_archivo(self):
        figuras = graficas.generar_figuras(self.leer(familia_sintetica()))
        rutas = graficas.guardar_figuras(figuras, Path(self.tmp.name) / "figuras")
        self.assertEqual([Path(r).name for r in rutas],
                         ["d1_marhamah_wq_niveles.png", "d1_marhamah_wq_global_erlang.png",
                          "d1_marhamah_utilizacion_ociosidad.png"])
        for ruta in rutas:
            self.assertTrue(Path(ruta).is_file())
            self.assertGreater(Path(ruta).stat().st_size, 0)

    def test_no_muta_datos_leidos(self):
        filas = self.leer(familia_sintetica())
        antes = copy.deepcopy(filas)
        graficas.generar_figuras(filas, sintetico=True)
        self.assertEqual(filas, antes)

    def cli(self, *args):
        entorno = dict(os.environ)
        entorno.pop("PYTHONPATH", None)
        return subprocess.run([sys.executable, "-m", "src.vista.graficas", *args],
                              cwd=ROOT, env=entorno, capture_output=True, text=True)

    def test_cli_ayuda(self):
        r = self.cli("--help")
        self.assertEqual(r.returncode, 0, r.stderr)
        for texto in ("resumen", "--salida", "--sintetico"):
            self.assertIn(texto, r.stdout)

    def test_cli_genera_figuras(self):
        escribir_csv(self.resumen, familia_sintetica())
        salida = Path(self.tmp.name) / "fig"
        r = self.cli(str(self.resumen), "--salida", str(salida), "--sintetico")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("datos sintéticos", r.stdout.lower())
        self.assertIn("d1_marhamah_wq_niveles.png", r.stdout)
        self.assertEqual(sorted(p.name for p in salida.iterdir()),
                         ["d1_marhamah_utilizacion_ociosidad.png",
                          "d1_marhamah_wq_global_erlang.png", "d1_marhamah_wq_niveles.png"])

    def test_cli_rechaza_entrada_invalida(self):
        salida = Path(self.tmp.name) / "fig"
        basura = Path(self.tmp.name) / "basura.csv"
        basura.write_text("a,b\n1,2\n", encoding="utf-8")
        for entrada in (Path(self.tmp.name) / "no_existe.csv", basura):
            with self.subTest(entrada=entrada.name):
                r = self.cli(str(entrada), "--salida", str(salida))
                self.assertEqual(r.returncode, 2, r.stderr)
                self.assertNotIn("Traceback", r.stderr)
                self.assertFalse(salida.exists())


if __name__ == "__main__":
    unittest.main()
