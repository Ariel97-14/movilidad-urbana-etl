import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from movilidad.pipeline import import_trips, make_report


FIELDS = ["trip_id", "started_at", "ended_at", "start_station", "end_station"]


def write_csv(path, rows, fields=FIELDS):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "trips.csv"
        self.database = self.root / "trips.sqlite3"

    def test_import_is_idempotent_and_report_aggregates(self):
        write_csv(self.source, [
            {"trip_id": "T-001", "started_at": "2026-01-05T08:00:00-03:00", "ended_at": "2026-01-05T08:20:00-03:00", "start_station": "Centro", "end_station": "Parque"},
            {"trip_id": "T-002", "started_at": "2026-01-06T09:00:00-03:00", "ended_at": "2026-01-06T09:40:00-03:00", "start_station": "Centro", "end_station": "Terminal"},
            {"trip_id": "T-003", "started_at": "2026-02-02T10:00:00-03:00", "ended_at": "2026-02-02T10:10:00-03:00", "start_station": "Parque", "end_station": "Centro"},
        ])
        self.assertEqual(import_trips(self.source, self.database), {"inserted": 3, "duplicates": 0, "rejected": 0})
        self.assertEqual(import_trips(self.source, self.database), {"inserted": 0, "duplicates": 3, "rejected": 0})
        self.assertEqual(make_report(self.database), {
            "total_trips": 3,
            "total_minutes": 70,
            "busiest_start_station": "Centro",
            "trips_by_month": {"2026-01": 2, "2026-02": 1},
        })

    def test_invalid_rows_are_rejected_without_stopping_import(self):
        write_csv(self.source, [
            {"trip_id": "T-001", "started_at": "2026-01-05T08:00:00Z", "ended_at": "2026-01-05T08:20:00Z", "start_station": "Centro", "end_station": "Parque"},
            {"trip_id": "T-002", "started_at": "2026-01-05T09:00:00Z", "ended_at": "2026-01-05T08:00:00Z", "start_station": "Centro", "end_station": "Parque"},
            {"trip_id": "T-003", "started_at": "fecha-invalida", "ended_at": "2026-01-05T10:00:00Z", "start_station": "Centro", "end_station": "Parque"},
            {"trip_id": "T-004", "started_at": "2026-01-05T10:00:00Z", "ended_at": "2026-01-05T10:10:00Z", "start_station": "", "end_station": "Parque"},
            {"trip_id": "T-005", "started_at": "2026-01-05T10:00:00Z", "ended_at": "2026-01-05T10:00:00.500000Z", "start_station": "Centro", "end_station": "Parque"},
        ])
        self.assertEqual(import_trips(self.source, self.database), {"inserted": 1, "duplicates": 0, "rejected": 4})
        self.assertEqual(make_report(self.database)["total_trips"], 1)

    def test_missing_required_column_fails_before_import(self):
        write_csv(self.source, [{"trip_id": "T-001"}], fields=["trip_id"])
        with self.assertRaisesRegex(ValueError, "columnas"):
            import_trips(self.source, self.database)

    def test_cli_emits_json(self):
        write_csv(self.source, [{"trip_id": "T-001", "started_at": "2026-01-05T08:00:00Z", "ended_at": "2026-01-05T08:30:00Z", "start_station": "Centro", "end_station": "Parque"}])
        command = [sys.executable, "-m", "movilidad", "import", str(self.source), "--db", str(self.database)]
        imported = subprocess.run(command, capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(imported.stdout)["inserted"], 1)
        report = subprocess.run([sys.executable, "-m", "movilidad", "report", "--db", str(self.database)], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(report.stdout)["total_minutes"], 30)


if __name__ == "__main__":
    unittest.main()

