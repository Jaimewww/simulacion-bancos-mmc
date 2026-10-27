"""Observed metrics contract and computation (Alex, task C1).

Consume client records and DES time integrals. Compute per-level waits,
time-average queues and utilization. Report window boundaries and pending
clients explicitly; draining must not extend window denominators. Little's
law is an asymptotic consistency check, not an exact finite-horizon
assertion.
"""

import math
from typing import Any

from .cliente import Cliente, EstadoCliente, Nivel
from .resultados import ResultadoCorrida, TipoEvento


def _es_numero_valido(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _medias_espera_por_nivel(clientes: tuple[Cliente, ...]) -> dict[Nivel, dict[str, float | None]]:
    resumen = {}
    for nivel in Nivel:
        del_nivel = [c for c in clientes if c.nivel is nivel]
        esperas = []
        for c in del_nivel:
            if c.t_inicio_servicio is not None:
                w = c.t_inicio_servicio - c.t_llegada
                if w < 0:
                    raise ValueError(f"espera negativa para cliente {c.id_llegada}")
                esperas.append(w)
        if esperas:
            wq_prom = sum(esperas) / len(esperas)
            resumen[nivel] = {"Wq_prom_muestra": wq_prom, "n_muestra_inicio": len(esperas)}
        else:
            resumen[nivel] = {"Wq_prom_muestra": None, "n_muestra_inicio": 0}
    return resumen


def _medias_sistema_por_nivel(clientes: tuple[Cliente, ...]) -> dict[Nivel, dict[str, float | None]]:
    resumen = {}
    for nivel in Nivel:
        del_nivel = [c for c in clientes if c.nivel is nivel]
        sist = []
        serv = []
        for c in del_nivel:
            if c.t_fin_servicio is not None and c.t_inicio_servicio is not None:
                sist.append(c.t_fin_servicio - c.t_llegada)
                serv.append(c.t_fin_servicio - c.t_inicio_servicio)
        resumen[nivel] = {
            "W_prom_muestra": (sum(sist) / len(sist)) if sist else None,
            "Ws_prom_muestra": (sum(serv) / len(serv)) if serv else None,
            "n_muestra_completo": len(sist),
        }
    return resumen


def calcular_metricas_observadas(resultado: ResultadoCorrida) -> dict[str, Any]:
    if not isinstance(resultado, ResultadoCorrida):
        raise TypeError("resultado debe ser ResultadoCorrida")

    m = dict(resultado.metricas)
    p = resultado.parametros
    ventana = p.horizon - p.warmup
    if ventana <= 0:
        raise ValueError("ventana de medición inválida")

    conteos = resultado.conteos

    cohorte = tuple(c for c in resultado.clientes if p.warmup <= c.t_llegada <= p.horizon)
    espera_nivel = _medias_espera_por_nivel(cohorte)
    sist_nivel = _medias_sistema_por_nivel(cohorte)

    lq_pref = m.get("lq_preferencial")
    lq_gen = m.get("lq_general")
    lq_global = m.get("lq_global")
    utilizacion = m.get("utilizacion")

    pendientes_total = sum(c.pendientes for c in conteos.values())
    atendidos_total = sum(c.atendidos for c in conteos.values())
    ingresados_total = sum(c.ingresados for c in conteos.values())

    out = {
        "unidad": str(p.unidad.value),
        "nombre_escenario": p.nombre,
        "disciplina": resultado.disciplina.value,
        "semilla": resultado.semilla,
        "inicio_medicion": p.warmup,
        "fin_medicion": p.horizon,
        "ventana_medida": ventana,
        "calentamiento": p.warmup,
        "horizonte": p.horizon,
        "no_se_extiende_ventana_por_drenaje": True,
        "conteos_por_nivel": {
            nivel.name: {
                "ingresados": c.ingresados,
                "atendidos": c.atendidos,
                "pendientes": c.pendientes,
                "en_cola": sum(x.nivel is nivel and x.estado is EstadoCliente.EN_COLA for x in resultado.clientes),
                "en_servicio": sum(x.nivel is nivel and x.estado is EstadoCliente.EN_SERVICIO for x in resultado.clientes),
            }
            for nivel, c in conteos.items()
        },
        "pendientes_en_cola_o_servicio": pendientes_total,
        "atendidos_total": atendidos_total,
        "ingresados_total": ingresados_total,
        "clientes_incompletos_tratamiento": "esperas/desviaciones desconocidas permanecen None; no se convierten a 0",
        "Lq_temporal": {
            "preferencial": lq_pref,
            "general": lq_gen,
            "global": lq_global,
        },
        "utilizacion": utilizacion,
        "Wq_por_nivel_muestra_inicio": {
            nivel.name: espera_nivel[nivel] for nivel in Nivel
        },
        "W_sistema_por_nivel_muestra_completa": {
            nivel.name: sist_nivel[nivel] for nivel in Nivel
        },
        "areas_temporales": {
            k: m.get(k) for k in ("area_cola_preferencial", "area_cola_general", "area_ocupados")
        },
    }
    esperas = [c.t_inicio_servicio - c.t_llegada for c in cohorte if c.t_inicio_servicio is not None]
    out["Wq_global_muestra"] = sum(esperas) / len(esperas) if esperas else None
    out["n_muestra_inicio_global"] = len(esperas)
    for estado in ("en_cola", "en_servicio"):
        out["pendientes_" + estado] = sum(v[estado] for v in out["conteos_por_nivel"].values())
    return out


def comprobacion_little(resultado: ResultadoCorrida, tol: float = 0.2) -> dict[str, Any]:
    """Finite-window area identity and asymptotic Little diagnostic.

    20% is an exploratory relative tolerance, not a statistical acceptance test.
    Clipped waits include carry-in and censored queues, hence the area identity
    is exact up to floating point error even when cohort Little is biased.
    """
    p = resultado.parametros
    obs = calcular_metricas_observadas(resultado)
    checks = []
    for nivel in (*Nivel, None):
        clientes = [c for c in resultado.clientes if nivel is None or c.nivel is nivel]
        nombre = nivel.name if nivel is not None else "GLOBAL"
        lq = obs["Lq_temporal"][nivel.name.lower() if nivel is not None else "global"]
        area = sum(max(0, min(c.t_inicio_servicio if c.t_inicio_servicio is not None else p.horizon, p.horizon) - max(c.t_llegada, p.warmup)) for c in clientes)
        reconstruido = area / obs["ventana_medida"]
        cohorte = [c for c in clientes if c.t_llegada >= p.warmup]
        tasa = len(cohorte) / obs["ventana_medida"]
        wq = obs["Wq_global_muestra"] if nivel is None else obs["Wq_por_nivel_muestra_inicio"][nombre]["Wq_prom_muestra"]
        producto = tasa * wq if wq is not None else None
        diferencia = lq - producto if lq is not None and producto is not None else None
        checks.append({"nivel": nombre, "Lq_temporal": lq, "tasa_llegadas_observada": tasa,
                       "Wq_muestra": wq, "lambda_Wq": producto, "diferencia": diferencia,
                       "dentro_tol": abs(diferencia) <= tol * max(abs(lq), abs(producto), 1e-12) if diferencia is not None else None,
                       "Lq_reconstruido_bordes": reconstruido,
                       "diferencia_identidad": lq - reconstruido if lq is not None else None,
                       "identidad_ok": math.isclose(lq, reconstruido, rel_tol=1e-9, abs_tol=1e-9) if lq is not None else None})
    return {"comprobaciones_little": checks, "tolerancia": tol,
            "nota": "diagnostico asintotico; censura y arrastre inicial afectan la cohorte; identidad usa esperas recortadas"}


def conservacion_clientes(resultado: ResultadoCorrida) -> dict[str, Any]:
    detalles = []
    for nivel, conteo in resultado.conteos.items():
        clientes = [c for c in resultado.clientes if c.nivel is nivel]
        ids = {c.id_llegada for c in clientes}
        eventos = [e for e in resultado.eventos if e.cliente_id in ids]
        llegadas = sum(e.tipo is TipoEvento.LLEGADA for e in eventos)
        inicios = sum(e.tipo is TipoEvento.INICIO_SERVICIO for e in eventos)
        fines = sum(e.tipo is TipoEvento.FIN_SERVICIO for e in eventos)
        cola = sum(c.estado is EstadoCliente.EN_COLA for c in clientes)
        servicio = sum(c.estado is EstadoCliente.EN_SERVICIO for c in clientes)
        diferencias = {"balance_registros": conteo.ingresados - conteo.atendidos - cola - servicio,
                       "llegadas_vs_registros": llegadas - conteo.ingresados,
                       "fines_vs_atendidos": fines - conteo.atendidos,
                       "balance_cola_eventos": llegadas - inicios - cola,
                       "balance_servicio_eventos": inicios - fines - servicio}
        detalles.append({"nivel": nivel.name, "ingresados": conteo.ingresados, "atendidos": conteo.atendidos,
                         "pendientes": conteo.pendientes, "en_cola": cola, "en_servicio": servicio,
                         "llegadas_eventos": llegadas, "inicios_eventos": inicios, "fines_eventos": fines,
                         "diferencias": diferencias, "ok": all(v == 0 for v in diferencias.values())})
    return {"conservacion_ok": all(d["ok"] for d in detalles), "detalles": detalles,
            "tolerancia": 0, "nota": "conteos enteros y flujos de eventos; sin tolerancia estadistica"}
