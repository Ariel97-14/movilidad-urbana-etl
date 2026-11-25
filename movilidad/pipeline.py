"""Importación idempotente y métricas de viajes sintéticos."""

import csv
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_COLUMNS = {"trip_id", "started_at", "ended_at", "start_station", "end_station"}


def _connect(database: Path) -> sqlite3.Connection:
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    connection.execute("""
        CREATE TABLE IF NOT EXISTS trips (
            trip_id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL,
            ended_at TEXT NOT NULL,
            start_station TEXT NOT NULL,
            end_station TEXT NOT NULL,
            duration_seconds INTEGER NOT NULL CHECK (duration_seconds > 0)
        )
    """)
    return connection


def _parse_trip(row: dict) -> tuple:
    trip_id = (row.get("trip_id") or "").strip()
    origin = (row.get("start_station") or "").strip()
    destination = (row.get("end_station") or "").strip()
    if not trip_id or not origin or not destination:
        raise ValueError("ID y estaciones obligatorios")
    try:
        started = datetime.fromisoformat((row.get("started_at") or "").replace("Z", "+00:00"))
        ended = datetime.fromisoformat((row.get("ended_at") or "").replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("Fecha ISO 8601 inválida") from error
    if started.tzinfo is None or ended.tzinfo is None:
        raise ValueError("Las fechas deben incluir zona horaria")
    duration = (ended - started).total_seconds()
    if not 1 <= duration <= 24 * 60 * 60 or not duration.is_integer():
        raise ValueError("La duración debe tener segundos enteros y ser de hasta 24 horas")
    return (
        trip_id,
        started.astimezone(timezone.utc).isoformat(),
        ended.astimezone(timezone.utc).isoformat(),
        origin,
        destination,
        int(duration),
    )


def import_trips(source: Path, database: Path) -> dict:
    """Importa filas válidas; cuenta duplicados y rechazos sin revelar su contenido."""
    source, database = Path(source), Path(database)
    with source.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
            raise ValueError("Faltan columnas requeridas en el CSV")
        counts = {"inserted": 0, "duplicates": 0, "rejected": 0}
        with closing(_connect(database)) as connection, connection:
            for row in reader:
                try:
                    trip = _parse_trip(row)
                except ValueError:
                    counts["rejected"] += 1
                    continue
                cursor = connection.execute(
                    "INSERT OR IGNORE INTO trips VALUES (?, ?, ?, ?, ?, ?)", trip
                )
                counts["inserted" if cursor.rowcount else "duplicates"] += 1
        return counts


def make_report(database: Path) -> dict:
    """Devuelve métricas en UTC; un empate de estaciones usa orden alfabético."""
    with closing(_connect(Path(database))) as connection:
        totals = connection.execute(
            "SELECT count(*) AS total_trips, COALESCE(sum(duration_seconds), 0) AS total_seconds FROM trips"
        ).fetchone()
        busiest = connection.execute(
            "SELECT start_station FROM trips GROUP BY start_station ORDER BY count(*) DESC, start_station ASC LIMIT 1"
        ).fetchone()
        months = connection.execute(
            "SELECT substr(started_at, 1, 7) AS month, count(*) AS trips FROM trips GROUP BY month ORDER BY month"
        ).fetchall()
        return {
            "total_trips": totals["total_trips"],
            "total_minutes": round(totals["total_seconds"] / 60, 2),
            "busiest_start_station": busiest["start_station"] if busiest else None,
            "trips_by_month": {row["month"]: row["trips"] for row in months},
        }

