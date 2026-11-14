from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from map_data_format import canonical


def decode_constant(text: str, name: str):
    marker = f"const {name} = "
    start = text.index(marker) + len(marker)
    return json.JSONDecoder().raw_decode(text[start:])[0]


def summarize(path: Path):
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        payload = json.loads(text)
    else:
        payload = {"datasets": decode_constant(text, "MAP_DATASETS"), "metadata": decode_constant(text, "MAP_METADATA")}
    # Compare in one canonical form so the compact site file and a full build agree.
    payload = canonical(payload)
    datasets = payload["datasets"]
    metadata = payload["metadata"]
    summary = {"years": metadata["years"], "datasets": {}}
    for dataset_key, dataset in datasets.items():
        sources = {}
        for source_key, source in dataset["sources"].items():
            canonical_items = json.dumps(source["items"], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            sources[source_key] = {
                "items": len(source["items"]),
                "itemIds": sorted(source["items"]),
                "contentSha256": hashlib.sha256(canonical_items).hexdigest(),
                "unmatched": len(source.get("unmatched", [])),
                "stateTotals": source["stateTotals"],
            }
        summary["datasets"][dataset_key] = sources
    return summary


def compare(expected, actual, path="root", tolerance=1e-9, errors=None):
    errors = errors if errors is not None else []
    if isinstance(expected, dict) and isinstance(actual, dict):
        if set(expected) != set(actual):
            errors.append(f"{path}: key mismatch")
        for key in sorted(set(expected) & set(actual)):
            compare(expected[key], actual[key], f"{path}.{key}", tolerance, errors)
    elif isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            errors.append(f"{path}: length {len(actual)} != {len(expected)}")
        for index, (left, right) in enumerate(zip(expected, actual)):
            compare(left, right, f"{path}[{index}]", tolerance, errors)
    elif isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        if not math.isclose(float(expected), float(actual), rel_tol=tolerance, abs_tol=tolerance):
            errors.append(f"{path}: {actual} != {expected}")
    elif expected != actual:
        errors.append(f"{path}: {actual!r} != {expected!r}")
    return errors


def main():
    parser = argparse.ArgumentParser(description="Validate generated map data and optionally compare it with a regression baseline.")
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--report", type=Path, default=Path("build/validation-report.json"))
    parser.add_argument("--allow-change", action="store_true")
    parser.add_argument("--write-summary", type=Path)
    args = parser.parse_args()

    candidate = summarize(args.candidate)
    errors = []
    if candidate["years"] != sorted(candidate["years"]):
        errors.append("School years are not sorted")
    if len(candidate["years"]) < 8:
        errors.append("Candidate contains fewer than eight school years")
    for dataset_key in ("raw", "approximated"):
        if dataset_key not in candidate["datasets"]:
            errors.append(f"Missing dataset: {dataset_key}")
            continue
        for source_key in ("district", "isd", "region", "county"):
            if not candidate["datasets"][dataset_key].get(source_key, {}).get("items"):
                errors.append(f"Missing populated source: {dataset_key}.{source_key}")

    differences = []
    if args.baseline:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8")) if args.baseline.suffix.lower() == ".json" else summarize(args.baseline)
        differences = compare(baseline, candidate)
        if differences and not args.allow_change:
            errors.append("Candidate differs from the approved regression baseline")

    report = {"status": "pass" if not errors else "fail", "years": candidate["years"], "errors": errors, "differenceCount": len(differences), "differences": differences[:200]}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.write_summary:
        args.write_summary.parent.mkdir(parents=True, exist_ok=True)
        args.write_summary.write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "years": report["years"], "differenceCount": report["differenceCount"]}))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
