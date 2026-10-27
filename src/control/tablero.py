"""CLI del tablero D2: una captura estática de una corrida real del motor.

Orquesta el escenario documentado (A1), ejecuta una réplica con `MotorDES`
(B2) y delega la reconstrucción y el dibujo a la vista D2. La vista no llama
al motor y el tablero no altera la corrida: solo lee su registro de eventos.

Uso:
    python -m src.control.tablero --familia marhamah --c 3 --p 0.3 \\
        --origen-p "supuesto experimental" --horizon 480 --warmup 60 \\
        --semilla 12345 --instante 300 --salida salidas/tablero/tablero.png

p, origen de p, horizonte y calentamiento son obligatorios: no se inventan.
`--instante` omite el valor y usa el horizonte de la corrida; el rótulo lo
indica. La entrada inválida se rechaza con código 2 antes de escribir el PNG.
"""

import argparse
import os

import matplotlib.pyplot as plt

from ..modelo.motor_des import MotorDES
from ..modelo.parametros import ADAMS_YEBOAH, MARHAMAH, crear_escenario
from ..modelo.resultados import Disciplina
from ..vista.animacion import dibujar_tablero, reconstruir_tablero

_FAMILIAS = {"adams_yeboah": ADAMS_YEBOAH, "marhamah": MARHAMAH}
_DISCIPLINAS = {"fcfs": Disciplina.FCFS, "prioridad": Disciplina.PRIORIDAD}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m src.control.tablero",
        description="Tablero D2: captura estática (PNG) de cajeros y colas desde "
                    "el registro de eventos de UNA corrida real. No simula dos veces.")
    parser.add_argument("--familia", choices=sorted(_FAMILIAS), default="marhamah",
                        help="familia documentada (por defecto marhamah)")
    parser.add_argument("--c", type=int, default=3,
                        help="número de cajeros; debe pertenecer a la familia (por defecto 3)")
    parser.add_argument("--p", type=float, required=True,
                        help="proporción preferencial, supuesto experimental en [0, 1]")
    parser.add_argument("--origen-p", dest="origen_p", required=True,
                        help="fuente o supuesto declarado de p (no se inventa)")
    parser.add_argument("--horizon", type=float, required=True,
                        help="horizonte de la corrida en la unidad de la familia")
    parser.add_argument("--warmup", type=float, required=True,
                        help="calentamiento de la corrida; 0 <= warmup < horizon")
    parser.add_argument("--semilla", type=int, default=12345,
                        help="semilla entera >= 0 de la réplica (por defecto 12345)")
    parser.add_argument("--disciplina", choices=sorted(_DISCIPLINAS),
                        default="prioridad",
                        help="disciplina de la corrida (por defecto prioridad)")
    parser.add_argument("--instante", type=float, default=None,
                        help="instante a dibujar dentro de [0, horizon]; si se omite "
                             "se usa el horizonte y el rótulo lo indica")
    parser.add_argument("--salida", default="salidas/tablero/tablero.png",
                        help="ruta del PNG (por defecto salidas/tablero/tablero.png)")
    args = parser.parse_args(argv)

    try:
        parametros = crear_escenario(
            _FAMILIAS[args.familia], args.c, args.p, origen_p=args.origen_p,
            horizon=args.horizon, warmup=args.warmup, seed=args.semilla)
        resultado = MotorDES(parametros, _DISCIPLINAS[args.disciplina],
                             semilla=args.semilla).correr()
        en_horizonte = args.instante is None
        instante = parametros.horizon if en_horizonte else args.instante
        estado = reconstruir_tablero(resultado, instante)
    except (TypeError, ValueError) as exc:
        parser.error(str(exc))

    fig = dibujar_tablero(estado)
    try:
        directorio = os.path.dirname(os.path.abspath(args.salida))
        os.makedirs(directorio, exist_ok=True)
        fig.savefig(args.salida, dpi=150)
    except OSError as exc:
        parser.error(f"no se pudo escribir {args.salida!r}: {exc}")
    finally:
        plt.close(fig)

    reloj = f"instante {estado.instante:g} {estado.unidad}"
    if en_horizonte:
        reloj += " (horizonte)"
    cajeros = ", ".join("libre" if cliente is None else f"cliente {cliente}"
                        for cliente in estado.cajeros)
    print(f"Tablero D2: {reloj}")
    print(f"Corrida: {estado.familia}|c={len(estado.cajeros)} · semilla "
          f"{estado.semilla} · disciplina {estado.disciplina.value} · p={estado.p:g} "
          f"· origen_p={estado.origen_p}")
    print(f"Cajeros ({len(estado.cajeros)}): {cajeros}")
    print(f"Esperando: preferencial {len(estado.cola_preferencial)}, "
          f"general {len(estado.cola_general)}")
    print(f"PNG: {args.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
