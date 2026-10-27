"""Figuras D1 del informe: espera por nivel, contraste con Erlang C y utilización.

Responsable: Jaime Landazuri (@Jaimewww) — tarea #4, aporte D1.

La vista es de solo lectura: consume el `resumen_*.csv` de la capa de control
C2 y no simula ni recalcula métricas. Los teóricos se copian tal cual de
`coherencia_json`. Una métrica vacía se conserva ausente (no se dibuja como
cero) y con n<2 no se agregan extremos de IC. Cada familia se dibuja aparte
con su unidad, p/origen_p e información de réplicas.

Uso: `python -m src.vista.graficas <resumen.csv> --salida <dir> [--sintetico]`

Tres figuras por familia: Wq preferencial/general por capacidad (FCFS y
prioridad), Wq global contra Erlang C y utilización ρ con ociosidad 1-ρ
(extremos del IC girados: 1-sup, 1-inf). `--sintetico` solo rotula datos
sintéticos; no genera datos. El backend de Matplotlib lo elige el entorno o
las pruebas (`MPLBACKEND=Agg`); la CLI cierra las figuras al terminar.
"""

import argparse
import csv
import json
import math
import os
import textwrap
from dataclasses import dataclass
from typing import NamedTuple

import matplotlib.pyplot as plt

METRICAS_IC = ("Wq_pref", "Wq_gen", "Wq_global", "Lq_global", "utilizacion")
_NIVELES = {"Wq_pref": "Wq preferencial", "Wq_gen": "Wq general"}
_DISCIPLINAS = {"fcfs": "FCFS", "prioridad": "Prioridad"}
_COLORES = {"fcfs": "#1f77b4", "prioridad": "#d62728"}
_NAN = float("nan")


@dataclass(frozen=True)
class Intervalo:
    """Media entre réplicas y extremos del IC95 %; `None` si no hay muestra."""

    media: float | None
    n: int
    inf: float | None
    sup: float | None


@dataclass(frozen=True)
class FilaResumen:
    """Una fila del resumen C2 ya normalizada para dibujar."""

    familia: str
    capacidad: int
    disciplina: str
    unidad: str
    p: float | None
    origen_p: str
    n_replicas: int
    intervalos: dict
    teoricos: dict


class Serie(NamedTuple):
    """Puntos de una métrica por capacidad; `nan` marca un valor no disponible."""

    capacidades: list
    medias: list
    inf: list
    sup: list


def _numero(valor):
    """Celda del CSV a float; vacío, 'nan' o texto no numérico -> None."""
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, str):
        valor = valor.strip()
        if valor in ("", "nan", "NaN", "None"):
            return None
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if math.isfinite(numero) else None


def _intervalo(fila, metrica):
    n = _numero(fila.get(metrica + "_n"))
    n = int(n) if n is not None else 0
    media = _numero(fila.get(metrica + "_media"))
    inf = _numero(fila.get(metrica + "_ic95_inf"))
    sup = _numero(fila.get(metrica + "_ic95_sup"))
    if media is None or n < 2:
        inf = sup = None  # sin réplicas suficientes no hay IC que dibujar
    return Intervalo(media, n, inf, sup)


def _teoricos(texto):
    """Valores teóricos por métrica, leídos de coherencia_json sin recalcular."""
    if not texto:
        return {}
    try:
        reportes = json.loads(texto)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"coherencia_json ilegible: {exc}") from exc
    teoricos = {}
    for reporte in reportes if isinstance(reportes, list) else []:
        if isinstance(reporte, dict) and reporte.get("tipo") == "erlang_c":
            valor = _numero(reporte.get("teorico"))
            if valor is not None:
                teoricos.setdefault(str(reporte.get("metrica")), valor)
    return teoricos


def _familia_capacidad(clave):
    partes = str(clave or "").split("|")
    if len(partes) != 2 or not partes[1].startswith("c="):
        raise ValueError(f"familia_c inesperada: {clave!r} (se esperaba 'familia|c=N')")
    try:
        capacidad = int(partes[1][2:])
    except ValueError as exc:
        raise ValueError(f"capacidad no entera en familia_c: {clave!r}") from exc
    if capacidad <= 0:
        raise ValueError(f"capacidad inválida en familia_c: {clave!r}")
    return partes[0], capacidad


def _normalizar(archivo):
    filas = []
    for cruda in csv.DictReader(archivo):
        familia, capacidad = _familia_capacidad(cruda.get("familia_c"))
        filas.append(FilaResumen(
            familia=familia, capacidad=capacidad,
            disciplina=(cruda.get("disciplina") or "").strip(),
            unidad=(cruda.get("unidad") or "").strip(),
            p=_numero(cruda.get("p")),
            origen_p=(cruda.get("origen_p") or "").strip(),
            n_replicas=int(_numero(cruda.get("n_replicas")) or 0),
            intervalos={m: _intervalo(cruda, m) for m in METRICAS_IC},
            teoricos=_teoricos(cruda.get("coherencia_json"))))
    return filas


def cargar_resumen(ruta):
    """Lee un `resumen_*.csv` y devuelve filas normalizadas (no altera el archivo)."""
    try:
        with open(ruta, newline="", encoding="utf-8") as archivo:
            return _normalizar(archivo)
    except OSError as exc:
        raise ValueError(f"no se pudo leer el resumen {os.fspath(ruta)!r}: {exc}") from exc


def invertir_intervalo(intervalo):
    """Ociosidad = 1 - utilización; el IC se gira a [1-sup, 1-inf]."""
    if intervalo.media is None:
        return Intervalo(None, intervalo.n, None, None)
    return Intervalo(1.0 - intervalo.media, intervalo.n,
                     None if intervalo.sup is None else 1.0 - intervalo.sup,
                     None if intervalo.inf is None else 1.0 - intervalo.inf)


def _nan(valor):
    return _NAN if valor is None else float(valor)


def serie_por_capacidad(filas, disciplina, metrica, invertir=False):
    """Puntos de `metrica` por capacidad de una disciplina, ordenados por c."""
    unicas = {}
    for fila in filas:
        if fila.disciplina != disciplina:
            continue
        if fila.capacidad in unicas:
            raise ValueError(f"capacidad duplicada para disciplina {disciplina!r}: c={fila.capacidad}")
        unicas[fila.capacidad] = fila
    intervalos = [unicas[c].intervalos.get(metrica) or Intervalo(None, 0, None, None)
                  for c in sorted(unicas)]
    if invertir:
        intervalos = [invertir_intervalo(i) for i in intervalos]
    return Serie(sorted(unicas),
                 [_nan(i.media) for i in intervalos],
                 [_nan(i.inf) for i in intervalos],
                 [_nan(i.sup) for i in intervalos])


def _orden_disciplinas(filas):
    presentes = list(dict.fromkeys(f.disciplina for f in filas))
    orden = list(_DISCIPLINAS)
    return sorted(presentes, key=lambda d: (orden.index(d) if d in orden else len(orden), d))


def _texto_n(intervalos):
    muestras = sorted({i.n for i in intervalos})
    if not muestras or muestras == [0]:
        return "sin muestra"
    return "n=" + ",".join(str(n) for n in muestras)


def _nombre(disciplina):
    return _DISCIPLINAS.get(disciplina, disciplina)


def _lista_unicos(valores):
    unicos = []
    for valor in valores:
        if valor not in unicos:
            unicos.append(valor)
    return unicos


def _validar_familia(filas):
    if not filas:
        raise ValueError("no hay filas para la familia")
    unidades = sorted({f.unidad for f in filas})
    if len(unidades) != 1:
        raise ValueError(f"unidad inconsistente en familia {filas[0].familia}: {unidades}")
    return unidades[0]


def _encabezado(filas, tema, sintetico=False):
    """Título con familia, unidad, p/origen_p y réplicas: nada queda implícito.

    Cada línea se ajusta al ancho de la figura para que no se recorte.
    """
    unidad = _validar_familia(filas)
    p = ", ".join(f"{v:g}" for v in _lista_unicos([f.p for f in filas]) if v is not None)
    origen = "; ".join(_lista_unicos([f.origen_p or "no declarado" for f in filas]))
    replicas = _lista_unicos([f.n_replicas for f in filas])
    texto_n = f"n={replicas[0]}" if len(replicas) == 1 else "n=" + ",".join(str(n) for n in replicas)
    lineas = [f"Familia {filas[0].familia} — {tema}"]
    if sintetico:
        lineas.append("DATOS SINTÉTICOS: no son resultados del estudio.")
    lineas += [f"Unidad: {unidad} · p={p or 'no declarada'} · réplicas por punto: {texto_n}",
               f"origen_p: {origen}"]
    return "\n".join(textwrap.fill(linea, 92) for linea in lineas)


def _nota(sintetico):
    """Leyenda de pie: método del IC y procedencia de los teóricos."""
    notas = ["DATOS SINTÉTICOS: no son resultados del estudio."] if sintetico else []
    notas.append("IC95 % t de Student entre réplicas; sin IC cuando n<2; "
                 "teóricos tomados de coherencia_json.")
    return textwrap.fill(" ".join(notas), 92)


def _barras(ax, serie, etiqueta, estilo):
    """Dibuja media e IC95 %; un punto sin IC queda sin barra, nunca en cero."""
    bajo = [m - i for m, i in zip(serie.medias, serie.inf, strict=True)]
    alto = [s - m for m, s in zip(serie.medias, serie.sup, strict=True)]
    hay_ic = any(not math.isnan(v) for v in bajo + alto)
    return ax.errorbar(serie.capacidades, serie.medias,
                       yerr=[bajo, alto] if hay_ic else None,
                       label=etiqueta, capsize=3, **estilo)


def _dibujar(ax, filas, series):
    """Una serie por disciplina para cada (metrica, texto, marca, trazo, invertir)."""
    for disciplina in _orden_disciplinas(filas):
        bloque = [f for f in filas if f.disciplina == disciplina]
        for metrica, texto, marca, trazo, invertir in series:
            muestras = _texto_n([f.intervalos[metrica] for f in bloque])
            _barras(ax, serie_por_capacidad(bloque, disciplina, metrica, invertir),
                    f"{_nombre(disciplina)} · {texto} ({muestras})",
                    {"color": _COLORES.get(disciplina, "black"), "marker": marca,
                     "linestyle": trazo, "linewidth": 1.3})


def _teorico(ax, filas, metrica, texto):
    """Curva teórica tal como la reporta coherencia_json; si falta, se avisa."""
    valores = {}
    for fila in filas:
        teorico = fila.teoricos.get(metrica)
        if teorico is not None:
            valores.setdefault(fila.capacidad, teorico)
    if not valores:
        ax.text(0.02, 0.98, "Sin valores analíticos en coherencia_json: no se dibuja la curva.",
                transform=ax.transAxes, va="top", fontsize=8)
        return
    puntos = sorted(valores)
    ax.plot(puntos, [valores[c] for c in puntos], "k:", marker="x", linewidth=1.1, label=texto)


def _terminar(fig, ax, filas, tema, ylabel, sintetico):
    # La nota va en el pie del eje X para que el layout no la superponga.
    ax.set_xlabel("Capacidad (número de cajeros c)\n" + _nota(sintetico), fontsize=9)
    ax.set_ylabel(ylabel)
    ax.set_xticks(sorted({f.capacidad for f in filas}))
    ax.set_title(_encabezado(filas, tema, sintetico), fontsize=9, loc="left")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    return fig


def _nueva_figura():
    return plt.subplots(figsize=(7.5, 5.2), layout="constrained")


def figura_wq_por_nivel(filas, sintetico=False):
    """F1: Wq preferencial y general por capacidad, FCFS y prioridad."""
    unidad = _validar_familia(filas)
    fig, ax = _nueva_figura()
    _dibujar(ax, filas, [("Wq_pref", _NIVELES["Wq_pref"], "o", "--", False),
                         ("Wq_gen", _NIVELES["Wq_gen"], "s", "-", False)])
    return _terminar(fig, ax, filas, "Wq por nivel y capacidad",
                     f"Wq por nivel ({unidad})", sintetico)


def figura_wq_global_vs_erlang_c(filas, sintetico=False):
    """F2: Wq global por disciplina contra el teórico de coherencia_json."""
    unidad = _validar_familia(filas)
    fig, ax = _nueva_figura()
    _dibujar(ax, filas, [("Wq_global", "Wq global", "o", "-", False)])
    _teorico(ax, filas, "Wq_global", "Erlang C (teórico)")
    return _terminar(fig, ax, filas, "Wq global vs Erlang C",
                     f"Wq global ({unidad})", sintetico)


def figura_utilizacion_ociosidad(filas, sintetico=False):
    """F3: utilización ρ y ociosidad 1-ρ; en 1-ρ los extremos del IC se giran."""
    fig, ax = _nueva_figura()
    _dibujar(ax, filas, [("utilizacion", "utilización ρ", "o", "-", False),
                         ("utilizacion", "ociosidad 1-ρ", "v", "--", True)])
    _teorico(ax, filas, "utilizacion", "ρ Erlang C (teórico)")
    return _terminar(fig, ax, filas, "Utilización y ociosidad por capacidad",
                     "Utilización ρ / ociosidad 1-ρ (fracción)", sintetico)


def textos_figura(fig):
    """Títulos, etiquetas, textos y leyendas de una figura (para comprobaciones)."""
    textos = [fig.get_suptitle()]
    for ax in fig.get_axes():
        textos += [ax.get_title(loc=lugar) for lugar in ("left", "center", "right")]
        textos += [ax.get_xlabel(), ax.get_ylabel()]
        textos += [texto.get_text() for texto in ax.texts]
        leyenda = ax.get_legend()
        if leyenda is not None:
            textos += [texto.get_text() for texto in leyenda.get_texts()]
    textos += [texto.get_text() for texto in fig.texts]
    return [texto for texto in textos if texto]


def generar_figuras(filas, sintetico=False):
    """Tres figuras por familia; claves 'familia|nombre' en orden de aparición."""
    figuras = {}
    for familia, bloque in _agrupar_por_familia(filas).items():
        figuras[f"{familia}|wq_niveles"] = figura_wq_por_nivel(bloque, sintetico)
        figuras[f"{familia}|wq_global_erlang"] = figura_wq_global_vs_erlang_c(bloque, sintetico)
        figuras[f"{familia}|utilizacion_ociosidad"] = figura_utilizacion_ociosidad(bloque, sintetico)
    return figuras


def _agrupar_por_familia(filas):
    grupos = {}
    for fila in filas:
        grupos.setdefault(fila.familia, []).append(fila)
    return grupos


def guardar_figuras(figuras, directorio, dpi=150):
    """Guarda cada figura como PNG y devuelve las rutas en orden de creación."""
    try:
        os.makedirs(directorio, exist_ok=True)
    except OSError as exc:
        raise ValueError(f"no se pudo crear el directorio {os.fspath(directorio)!r}: {exc}") from exc
    rutas = []
    for clave, fig in figuras.items():
        ruta = os.path.join(os.fspath(directorio), "d1_" + clave.replace("|", "_") + ".png")
        fig.savefig(ruta, dpi=dpi)
        rutas.append(ruta)
    return rutas


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m src.vista.graficas",
        description="Figuras D1 desde un resumen C2: Wq por nivel, Wq global vs Erlang C "
                    "y utilización/ociosidad. No simula ni recalcula métricas.")
    parser.add_argument("resumen", help="ruta del resumen_*.csv exportado por main.py")
    parser.add_argument("--salida", default="salidas/figuras", help="directorio de las figuras PNG")
    parser.add_argument("--dpi", type=int, default=150, help="resolución de salida (por defecto 150)")
    parser.add_argument("--sintetico", action="store_true",
                        help="rotula las figuras como datos sintéticos; no son resultados del estudio")
    args = parser.parse_args(argv)
    if args.dpi <= 0:
        parser.error("--dpi debe ser un entero positivo")
    try:
        filas = cargar_resumen(args.resumen)
        if not filas:
            parser.error("el resumen no contiene filas")
        figuras = generar_figuras(filas, sintetico=args.sintetico)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    try:
        try:
            rutas = guardar_figuras(figuras, args.salida, dpi=args.dpi)
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
    finally:
        for fig in figuras.values():
            plt.close(fig)
    if args.sintetico:
        print("Aviso: datos sintéticos; estas figuras no son resultados del estudio.")
    for ruta in rutas:
        print(f"Figura: {ruta}")
    print(f"Completado: {len(rutas)} figuras en {args.salida}. IC95% entre réplicas; "
          "sin τp/τg no se selecciona capacidad óptima.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
