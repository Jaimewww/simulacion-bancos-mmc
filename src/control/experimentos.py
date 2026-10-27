"""Scenario experiment matrix and run aggregation (Alex, task C2).

Runs both documented families (Adams & Yeboah c in {8..12}, Marhamah c in
{2..5}) comparing FCFS and non-preemptive priority with the same arrivals,
levels and preassigned service durations (reuse generar_carga and MotorDES
with carga). Records seeds, supports configurable warm-up/horizon/replicas.
Exports per-replica CSV and summary CSV with 95% confidence intervals.
Contrasts aggregated metrics with Erlang C and checks Little/conservation
with tolerances (finite horizon effects noted). Reports pending clients.
"""

import math
from typing import Any, Iterable

from ..modelo.analitico import erlang_c_desde_parametros
from ..modelo.metricas import calcular_metricas_observadas, comprobacion_little, conservacion_clientes
from ..modelo.motor_des import MotorDES, generar_carga
from ..modelo.parametros import ADAMS_YEBOAH, MARHAMAH
from ..modelo.resultados import Disciplina


def _media_varianza_muestral(valores: list[float]) -> tuple[float, float | None, int]:
    n = len(valores)
    if n == 0:
        return float("nan"), None, 0
    media = sum(valores) / n
    if n == 1:
        return media, None, 1
    var = sum((x - media) ** 2 for x in valores) / (n - 1)
    return media, var, n


def intervalo_confianza_95(valores: list[float]) -> dict[str, Any]:
    from scipy.stats import t
    valores = [float(x) for x in valores if x is not None and not isinstance(x, bool) and math.isfinite(x)]
    media, var, n = _media_varianza_muestral(valores)
    out = {"n": n, "media": media if n else None, "ic95_inf": None, "ic95_sup": None,
           "metodo": "t de Student, gl=n-1", "nota": "muestras insuficientes" if n < 2 else "replicas independientes; medias aproximadamente normales"}
    if n >= 2:
        ee = math.sqrt(var / n)
        margen = float(t.ppf(0.975, n - 1)) * ee
        out.update(var_muestral=var, ee=ee, gl=n-1, ic95_inf=media-margen, ic95_sup=media+margen)
    return out


def _semillas_para_replicas(semilla_base: int, repeticiones: int) -> list[int]:
    if not isinstance(repeticiones, int) or isinstance(repeticiones, bool) or repeticiones <= 0:
        raise ValueError("repeticiones debe ser un entero positivo")
    if not isinstance(semilla_base, int) or isinstance(semilla_base, bool) or semilla_base < 0:
        raise ValueError("semilla_base debe ser un entero >= 0")
    return [semilla_base + i for i in range(repeticiones)]


def ejecutar_replicas(parametros, disciplina: Disciplina, repeticiones: int, semilla_base: int):
    semillas = _semillas_para_replicas(semilla_base, repeticiones)
    resultados = []
    for s in semillas:
        carga = generar_carga(parametros, s)
        motor = MotorDES(parametros, disciplina, semilla=s, carga=carga)
        resultados.append(motor.correr())
    return resultados, semillas


def _extraer_metrica_agregada(run) -> dict[str, Any]:
    obs = calcular_metricas_observadas(run)
    wq_pref = obs["Wq_por_nivel_muestra_inicio"]["PREFERENCIAL"].get("Wq_prom_muestra")
    wq_gen = obs["Wq_por_nivel_muestra_inicio"]["GENERAL"].get("Wq_prom_muestra")
    lq_g = obs["Lq_temporal"].get("global")
    util = obs["utilizacion"]
    return {
        "Wq_pref": wq_pref, "Wq_gen": wq_gen,
        "Wq_global": obs["Wq_global_muestra"], "Lq_global": lq_g,
        "utilizacion": util, "pendientes_prom": obs["pendientes_en_cola_o_servicio"],
        "pendientes_en_cola": obs["pendientes_en_cola"],
        "pendientes_en_servicio": obs["pendientes_en_servicio"],
    }


def agregar_replicas(runs: list[Any]) -> dict[str, Any]:
    filas = [_extraer_metrica_agregada(r) for r in runs]
    nombres = ("Wq_pref", "Wq_gen", "Wq_global", "Lq_global", "utilizacion", "pendientes_prom", "pendientes_en_cola", "pendientes_en_servicio")
    return {**{k: intervalo_confianza_95([f[k] for f in filas]) for k in nombres}, "n_replicas": len(runs)}


def validar_coherencia(agregado: dict[str, Any], parametros) -> list[dict[str, Any]]:
    try:
        er = erlang_c_desde_parametros(parametros)
    except ValueError as e:
        return [{"tipo": "erlang_c", "ok": None, "error": str(e)}]
    reportes = []
    for metrica, teorico in (("Wq_global", er["Wq"]), ("Lq_global", er["Lq"]), ("utilizacion", er["rho"])):
        ic = agregado[metrica]
        media = ic["media"]
        inf, sup = ic["ic95_inf"], ic["ic95_sup"]
        reportes.append({"tipo": "erlang_c", "metrica": metrica, "teorico": teorico,
                         "observado": media, "diferencia": media-teorico if media is not None else None,
                         "n": ic["n"], "ic95_inf": inf, "ic95_sup": sup,
                         "compatible_ic95": inf <= teorico <= sup if inf is not None else None,
                         "nota": "IC entre replicas, sin tolerancia arbitraria; sesgo finito y comparaciones multiples; no prueba equivalencia"})
    return reportes


def _fam_obj(familia):
    if familia == 'adams_yeboah':
        return ADAMS_YEBOAH
    if familia == 'marhamah':
        return MARHAMAH
    raise ValueError(f"familia desconocida: {familia}")


def ejecutar_matriz(
    familias: Iterable[str] = ("adams_yeboah", "marhamah"),
    p: float = 0.3,
    origen_p: str = "supuesto_experimental_sin_dato_medido",
    horizon: float | None = None,
    warmup: float | None = None,
    repeticiones: int = 10,
    semilla_base: int = 12345,
    disciplinas: Iterable[Disciplina] = (Disciplina.FCFS, Disciplina.PRIORIDAD),
) -> dict[str, Any]:
    _semillas_para_replicas(semilla_base, repeticiones)
    familias, disciplinas = tuple(familias), tuple(disciplinas)
    resultados_matriz = {}
    semillas_registradas = {}
    for fam in familias:
        fam_obj = _fam_obj(fam)
        for c in fam_obj.capacidades:
            h = horizon if horizon is not None else (8.0 if fam == 'adams_yeboah' else 480.0)
            w = warmup if warmup is not None else (1.0 if fam == 'adams_yeboah' else 60.0)
            from ..modelo.parametros import crear_escenario
            params = crear_escenario(fam_obj, c, p, origen_p=origen_p, horizon=h, warmup=w)
            clave = f"{fam}|c={c}"
            resultados_matriz[clave] = {}
            semillas_registradas[clave] = {}
            for disc in disciplinas:
                runs, semillas = ejecutar_replicas(params, disc, repeticiones, semilla_base)
                agg = agregar_replicas(runs)
                coh = validar_coherencia(agg, params)
                resultados_matriz[clave][disc.value] = {
                    "runs": runs,
                    "semillas": semillas,
                    "agregado": agg,
                    "coherencia": coh,
                    "verificaciones_replicas": [{"semilla": r.semilla, "conservacion": conservacion_clientes(r), "little": comprobacion_little(r)} for r in runs],
                }
                semillas_registradas[clave][disc.value] = semillas
    return {
        "matriz": resultados_matriz,
        "semillas_registradas": semillas_registradas,
        "config": {
            "familias": list(familias),
            "p": p,
            "origen_p": origen_p,
            "horizon": horizon,
            "warmup": warmup,
            "repeticiones": repeticiones,
            "semilla_base": semilla_base,
            "disciplinas": [d.value for d in disciplinas],
        },
        "nota_proporcion_preferencial": f"p={p} declarado como supuesto experimental (origen_p={origen_p}); sin tau_p/tau_g definidos no se puede seleccionar capacidad óptima",
    }
