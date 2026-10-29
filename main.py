"""Experiment CLI for bank M/M/c simulations (Alex, task C2)."""

import argparse
import csv
import json
import os
from pathlib import Path
import sys

from src.modelo.resultados import Disciplina
from src.control import experimentos

RESULTADOS_PREDETERMINADOS = Path(__file__).resolve().parent.parent / "resultados_experimentos"


def _asegurar_dir(d):
    os.makedirs(d, exist_ok=True)
    return d


def _limpiar_resultados_generados(directorio):
    """Elimina solo salidas propias anteriores para conservar la última corrida."""
    base = Path(directorio)
    patrones = ("replicas.csv", "resumen.csv", "metadata.json",
                "replicas_[0-9]*.csv", "resumen_[0-9]*.csv",
                "metadata_[0-9]*.json")
    for patron in patrones:
        for ruta in base.glob(patron):
            if ruta.is_file():
                ruta.unlink()


def _argumentos_guiados() -> list[str]:
    """Solicita las dos decisiones experimentales necesarias para el informe."""
    print("\n==============================================")
    print(" SIMULACIÓN BANCARIA: RESULTADOS Y GRÁFICAS")
    print("==============================================")
    print("Se ejecutarán ambas familias: Marhamah y Adams–Yeboah.")
    print("La proporción preferencial indica qué parte del total de clientes")
    print("tiene prioridad; por ejemplo, 0.25 significa 25 %.")
    p = input("Proporción total de clientes preferenciales [0.25]: ").strip() or "0.25"
    replicas = input("Cantidad de réplicas [30]: ").strip() or "30"
    return ["--familia", "ambas", "--p", p, "--replicas", replicas,
            "--origen-p", "supuesto experimental ingresado en main.py"]


def main(argv=None) -> int:
    if argv is None and len(sys.argv) == 1:
        try:
            argv = _argumentos_guiados()
        except (EOFError, KeyboardInterrupt, ValueError) as exc:
            print(f"Entrada cancelada o inválida: {exc}", file=sys.stderr)
            return 2
    parser = argparse.ArgumentParser(description="Simulación bancos M/M/c - experimentos C2")
    parser.add_argument("--familia", choices=["adams_yeboah", "marhamah", "ambas"], default="ambas")
    parser.add_argument("--p", type=float, default=0.3,
                        help="proporción del total de clientes que es preferencial; 0.25 = 25%%")
    parser.add_argument("--origen-p", dest="origen_p", default="supuesto_experimental_sin_dato_medido")
    parser.add_argument("--horizon", type=float, default=None)
    parser.add_argument("--warmup", type=float, default=None)
    parser.add_argument("--replicas", type=int, default=10)
    parser.add_argument("--semilla-base", dest="semilla_base", type=int, default=12345)
    parser.add_argument("--salida", default=os.fspath(RESULTADOS_PREDETERMINADOS),
                        help="carpeta única de salida (por defecto, resultados_experimentos junto al repositorio)")
    parser.add_argument("--solo-fcfs", action="store_true")
    parser.add_argument("--solo-prioridad", action="store_true")
    args = parser.parse_args(argv)

    familias = ("adams_yeboah", "marhamah") if args.familia == "ambas" else (args.familia,)
    disciplinas = []
    if args.solo_fcfs and args.solo_prioridad:
        disciplinas = [Disciplina.FCFS, Disciplina.PRIORIDAD]
    elif args.solo_fcfs:
        disciplinas = [Disciplina.FCFS]
    elif args.solo_prioridad:
        disciplinas = [Disciplina.PRIORIDAD]
    else:
        disciplinas = [Disciplina.FCFS, Disciplina.PRIORIDAD]

    print("Inicio experimentos C2")
    print(f"Familias: {familias}, p={args.p} (origen_p={args.origen_p}), replicas={args.replicas}, semilla_base={args.semilla_base}")
    print("Nota: sin tau_p/tau_g definidos no se puede seleccionar capacidad óptima. p es supuesto experimental.")

    try:
        res = experimentos.ejecutar_matriz(
            familias=familias,
            p=args.p,
            origen_p=args.origen_p,
            horizon=args.horizon,
            warmup=args.warmup,
            repeticiones=args.replicas,
            semilla_base=args.semilla_base,
            disciplinas=disciplinas,
        )
    except (ValueError, TypeError) as exc:
        parser.error(str(exc))

    outdir = _asegurar_dir(args.salida)
    _limpiar_resultados_generados(outdir)
    per_rep = os.path.join(outdir, "replicas.csv")
    filas = []
    resumen_filas = []
    for clave, discmap in res["matriz"].items():
        for dname, info in discmap.items():
            for i, run in enumerate(info["runs"]):
                from src.modelo.metricas import calcular_metricas_observadas
                obs = calcular_metricas_observadas(run)
                fila = {"familia_c": clave, "disciplina": dname, "replica_idx": i,
                        "semilla": run.semilla, "unidad": obs["unidad"], "horizon": obs["horizonte"],
                        "warmup": obs["calentamiento"], "p": run.parametros.p, "origen_p": run.parametros.origen_p,
                        "ingresados_total": obs["ingresados_total"], "atendidos_total": obs["atendidos_total"],
                        "pendientes": obs["pendientes_en_cola_o_servicio"],
                        "pendientes_en_cola": obs["pendientes_en_cola"], "pendientes_en_servicio": obs["pendientes_en_servicio"],
                        "wq_global_muestra": obs["Wq_global_muestra"], "n_muestra_inicio_global": obs["n_muestra_inicio_global"],
                        "lq_global_temporal": obs["Lq_temporal"]["global"], "utilizacion": obs["utilizacion"]}
                for nivel, corto in (("PREFERENCIAL", "pref"), ("GENERAL", "gen")):
                    fila["wq_" + corto + "_muestra"] = obs["Wq_por_nivel_muestra_inicio"][nivel]["Wq_prom_muestra"]
                    fila["n_inicio_" + corto] = obs["Wq_por_nivel_muestra_inicio"][nivel]["n_muestra_inicio"]
                    for k, v in obs["conteos_por_nivel"][nivel].items():
                        fila[k + "_" + corto] = v
                    for k, v in obs["W_sistema_por_nivel_muestra_completa"][nivel].items():
                        fila[k + "_" + corto] = v
                ver = info["verificaciones_replicas"][i]
                fila["conservacion_ok"] = ver["conservacion"]["conservacion_ok"]
                fila["little_json"] = json.dumps(ver["little"], ensure_ascii=False)
                filas.append(fila)
            fila = {"familia_c": clave, "disciplina": dname, "n_replicas": info["agregado"]["n_replicas"],
                    "semillas": json.dumps(info["semillas"]), "unidad": run.unidad.value,
                    "horizon": run.parametros.horizon, "warmup": run.parametros.warmup,
                    "p": run.parametros.p, "origen_p": run.parametros.origen_p}
            for nombre, ic in info["agregado"].items():
                if isinstance(ic, dict):
                    for k in ("media", "n", "ic95_inf", "ic95_sup", "metodo", "nota"):
                        fila[nombre + "_" + k] = ic[k]
            # Retain the original C2 summary column names for consumers.
            for k in ("media", "ic95_inf", "ic95_sup"):
                fila["util_" + k] = info["agregado"]["utilizacion"][k]
            for nombre in ("Wq_pref", "Wq_gen"):
                fila[nombre + "_ic_metodo"] = info["agregado"][nombre]["metodo"]
            fila["coherencia_json"] = json.dumps(info["coherencia"], ensure_ascii=False)
            resumen_filas.append(fila)
    resumen = os.path.join(outdir, "resumen.csv")
    for ruta, datos in ((per_rep, filas), (resumen, resumen_filas)):
        with open(ruta, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(datos[0]))
            w.writeheader()
            w.writerows(datos)
        print(f"CSV: {ruta}")

    meta = os.path.join(outdir, "metadata.json")
    with open(meta, "w", encoding="utf-8") as f:
        json.dump({**res, "matriz": {k: {d: {campo: valor for campo, valor in info.items() if campo != "runs"} for d, info in ds.items()} for k, ds in res["matriz"].items()}}, f, indent=2, ensure_ascii=False, allow_nan=False)
    print(f"Metadata/semillas registradas: {meta}")
    from src.vista import graficas
    figuras_dir = os.path.join(outdir, "figuras")
    figuras = graficas.generar_figuras(graficas.cargar_resumen(resumen))
    try:
        rutas_figuras = graficas.guardar_figuras(figuras, figuras_dir)
    finally:
        for figura in figuras.values():
            graficas.plt.close(figura)
    for ruta in rutas_figuras:
        print(f"Figura: {ruta}")
    print(f"Completado. Resultados y gráficas actualizados en: {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
