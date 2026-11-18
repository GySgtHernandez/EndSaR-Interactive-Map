from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
BUILD = ROOT / "build"
REPORTS = ROOT / "reports"
WORKBOOK = BUILD / "CEPI_Seclusion_Restraint_Combined.xlsx"


def run(*args):
    print("+", " ".join(str(arg) for arg in args), flush=True)
    subprocess.run([str(arg) for arg in args], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description="Run the complete guarded CEPI-to-map data pipeline.")
    parser.add_argument("--discover", action="store_true", help="Update the manifest with newly discovered review candidates.")
    parser.add_argument("--baseline", type=Path, default=ROOT / "tests" / "baseline-summary.json")
    parser.add_argument("--allow-change", action="store_true")
    args = parser.parse_args()
    BUILD.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)

    download = [sys.executable, SCRIPTS / "download_sources.py", "--manifest", ROOT / "data" / "sources.json", "--output-dir", ROOT / "data" / "sources", "--report", REPORTS / "source-report.json"]
    if args.discover:
        download.append("--update-manifest")
    run(*download)
    if args.discover:
        run(sys.executable, SCRIPTS / "download_sources.py", "--manifest", ROOT / "data" / "sources.json", "--output-dir", ROOT / "data" / "sources", "--report", REPORTS / "source-report.json")
    run(sys.executable, SCRIPTS / "combine_cepi_workbooks.py", "--source-dir", ROOT / "data" / "sources", "--output", WORKBOOK)
    run(sys.executable, SCRIPTS / "add_projection_tabs.py", "--workbook", WORKBOOK, "--roster", ROOT / "data" / "district-roster.csv", "--regions", SCRIPTS / "isd-code-to-region.txt")
    run(sys.executable, SCRIPTS / "build_map_data.py", "--workbook", WORKBOOK, "--json-output", ROOT / "site" / "data" / "map-data.json")
    run(sys.executable, SCRIPTS / "export_entity_locations.py")
    run(sys.executable, SCRIPTS / "write_app_info.py")
    validate = [sys.executable, SCRIPTS / "validate_map_data.py", ROOT / "site" / "data" / "map-data.json", "--baseline", args.baseline, "--report", REPORTS / "validation-report.json"]
    if args.allow_change:
        validate.append("--allow-change")
    run(*validate)


if __name__ == "__main__":
    main()
