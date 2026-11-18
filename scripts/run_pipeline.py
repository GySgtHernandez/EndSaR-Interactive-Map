from __future__ import annotations

import argparse
import shutil
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
    run(sys.executable, SCRIPTS / "combine_cepi_workbooks.py", "--source-dir", ROOT / "data" / "sources", "--output", WORKBOOK, "--source-report", REPORTS / "source-report.json")
    build_periods(args)
    run(sys.executable, SCRIPTS / "export_entity_locations.py")
    run(sys.executable, SCRIPTS / "write_app_info.py")


# School Year Totals come only from CEPI's school-year sheets; each quarter only from its own
# quarter sheets. Nothing is added up across quarters.
PERIODS = [
    ("Full Year", "School Year Totals", "map-data.json", "baseline-summary.json", 8),
    ("Q1", "Q1", "map-data-q1.json", "baseline-summary-q1.json", 1),
    ("Q2", "Q2", "map-data-q2.json", "baseline-summary-q2.json", 1),
    ("Q3", "Q3", "map-data-q3.json", "baseline-summary-q3.json", 1),
    ("Q4", "Q4", "map-data-q4.json", "baseline-summary-q4.json", 1),
]


def build_periods(args, only=None):
    for period, label, output, baseline, min_years in PERIODS:
        if only and period not in only:
            continue
        folder = BUILD / output.replace(".json", "")
        folder.mkdir(exist_ok=True)
        workbook = folder / WORKBOOK.name  # same file name in every period's folder
        shutil.copyfile(WORKBOOK, workbook)
        run(sys.executable, SCRIPTS / "add_projection_tabs.py", "--workbook", workbook, "--roster", ROOT / "data" / "district-roster.csv", "--regions", SCRIPTS / "isd-code-to-region.txt", "--period", period)
        run(sys.executable, SCRIPTS / "build_map_data.py", "--workbook", workbook, "--json-output", ROOT / "site" / "data" / output, "--period", label)
        baseline_path = args.baseline if period == "Full Year" else ROOT / "tests" / baseline
        validate = [sys.executable, SCRIPTS / "validate_map_data.py", ROOT / "site" / "data" / output, "--baseline", baseline_path, "--report", REPORTS / output.replace("map-data", "validation-report"), "--min-years", min_years]
        if args.allow_change:
            validate.append("--allow-change")
        run(*validate)

if __name__ == "__main__":
    main()
