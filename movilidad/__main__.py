"""Interfaz de consola para el importador y los reportes."""

import argparse
import json
from pathlib import Path

from .pipeline import import_trips, make_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Analiza viajes ficticios de bicicletas")
    commands = parser.add_subparsers(dest="command", required=True)
    importer = commands.add_parser("import", help="Importar un CSV")
    importer.add_argument("source", type=Path)
    importer.add_argument("--db", type=Path, default=Path("movilidad.sqlite3"))
    reporter = commands.add_parser("report", help="Mostrar métricas en JSON")
    reporter.add_argument("--db", type=Path, default=Path("movilidad.sqlite3"))
    args = parser.parse_args()
    try:
        result = import_trips(args.source, args.db) if args.command == "import" else make_report(args.db)
    except (ValueError, FileNotFoundError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

