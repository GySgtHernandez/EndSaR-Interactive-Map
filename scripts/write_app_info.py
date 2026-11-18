"""Write site/data/app-info.json, shown in the map's "Updated" line and App Data panel.

- lastUpdated:    date the newest CEPI source file was added to the map (data/sources.json "importedOn")
- lastImportFile: that file's name
- lastRefreshed:  last time the update job checked the CEPI website (kept unless --refreshed is given)
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data" / "sources.json")
    parser.add_argument("--output", type=Path, default=ROOT / "site" / "data" / "app-info.json")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--refreshed", help="ISO time of the last CEPI check, e.g. 2026-11-16T22:27:10Z")
    group.add_argument("--refreshed-now", action="store_true", help="Record the current time as the last CEPI check")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    published = [s for s in manifest["sources"] if s.get("period") in manifest["policy"]["publishPeriods"] and s.get("status") != "superseded"]
    latest = max(published, key=lambda s: (s.get("importedOn", ""), s["schoolYear"]))
    previous = json.loads(args.output.read_text(encoding="utf-8")) if args.output.exists() else {}
    refreshed = previous.get("lastRefreshed")
    if args.refreshed_now:
        refreshed = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    elif args.refreshed:
        refreshed = args.refreshed
    # School years whose current CEPI file is a mid-year release, and which quarters it holds.
    quarters_by_year = {}
    for quarter in ("q1", "q2", "q3", "q4"):
        path = args.output.parent / f"map-data-{quarter}.json"
        if path.exists():
            for year in json.loads(path.read_text(encoding="utf-8"))["metadata"]["years"]:
                quarters_by_year.setdefault(year, []).append(quarter.upper())
    provisional = {s["schoolYear"]: {"file": Path(urlparse(s["url"]).path).name, "quarters": quarters_by_year.get(s["schoolYear"], [])}
                   for s in published if s["period"] != "full_year"}
    info = {
        "lastUpdated": latest.get("importedOn"),
        "lastImportFile": Path(urlparse(latest["url"]).path).name,
        "lastImportSchoolYear": latest["schoolYear"],
        "lastRefreshed": refreshed,
        "provisionalYears": provisional,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    print(f"app info -> {args.output}: {info}")


if __name__ == "__main__":
    main()
