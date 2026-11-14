"""Copy data/entity-locations.csv (easy to edit in Excel) to the JSON the map page loads.

These are map points for entities that have no district boundary: public school
academies (charters), ISD-run programs and state districts.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=ROOT / "data" / "entity-locations.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "site" / "data" / "entity-locations.json")
    args = parser.parse_args()
    points = {}
    with args.csv.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            code = row["district_code"].strip().zfill(5)
            kind = {"ISD": "isd", "PSA": "psa", "State District": "state"}.get(row.get("entity_type", "").strip(), "psa")
            points[code] = [round(float(row["latitude"]), 5), round(float(row["longitude"]), 5), 0 if row["location_source"].startswith("approximate") else 1, kind]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"fields": ["latitude", "longitude", "exact", "type"], "points": points}, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{len(points)} entity locations -> {args.output}")


if __name__ == "__main__":
    main()
