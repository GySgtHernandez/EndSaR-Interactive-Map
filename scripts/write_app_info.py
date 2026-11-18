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
    published = [s for s in manifest["sources"] if s.get("period") in manifest["policy"]["publishPeriods"]]
    latest = max(published, key=lambda s: (s.get("importedOn", ""), s["schoolYear"]))
    previous = json.loads(args.output.read_text(encoding="utf-8")) if args.output.exists() else {}
    refreshed = previous.get("lastRefreshed")
    if args.refreshed_now:
        refreshed = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    elif args.refreshed:
        refreshed = args.refreshed
    info = {
        "lastUpdated": latest.get("importedOn"),
        "lastImportFile": Path(urlparse(latest["url"]).path).name,
        "lastImportSchoolYear": latest["schoolYear"],
        "lastRefreshed": refreshed,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    print(f"app info -> {args.output}: {info}")


if __name__ == "__main__":
    main()
