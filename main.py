"""Scaffold entry point; experiment CLI belongs to Alex (task C2)."""

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bank M/M/c MVC scaffold; simulation not implemented yet."
    )
    parser.parse_args()
    print("Simulation not implemented yet. See docs/tasks.md.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
