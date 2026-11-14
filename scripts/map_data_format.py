"""Compact storage format for site/data/map-data.json (format 2).

The full map payload repeats most numbers several times (display copies, summary
copies, long runs of zero counters). Format 2 stores each value once and the map
page (and the validator) rebuild the full structure on load with expand().
Values are not changed: expand(compact(payload)) reproduces every metric,
summary, suppressed/approximated count and display string exactly.
"""
from __future__ import annotations

import copy

FORMAT_VERSION = 2
SUMMARY_FROM_METRIC = {
    "swd_total": "swd_students",
    "nonswd_total": "nonswd_students",
    "student_total": "all_students",
    "seclusion_total": "all_seclusions",
    "restraint_total": "all_restraints",
    "combined_event_total": "all_events",
}
TOP_FIELDS = ["district", "code", "total", "suppressed"]


def _shown(key: str, value) -> str:
    """Text the map shows for a number (1 decimal; ratio 3 decimals)."""
    digits = 3 if key == "event_student_ratio" else 1
    return f"{round(float(value or 0), digits):.{digits}f}"


def _compact_record(record: dict, keys: dict) -> dict:
    out = {}
    metrics = {k: v for k, v in record["metrics"].items() if v}
    if metrics:
        out["m"] = metrics
    display = {}
    for k, v in record.get("displayMetrics", {}).items():
        if isinstance(v, str) or _shown(k, v) != _shown(k, record["metrics"].get(k, 0)):
            display[k] = v
    if display:
        out["d"] = display
    for short, field in (("s", "suppressedCells"), ("a", "approximatedCells")):
        cells = {k: v for k, v in record.get(field, {}).items() if v}
        if cells:
            out[short] = cells
    for name, metric in SUMMARY_FROM_METRIC.items():
        if abs(record["summary"][name] - record["metrics"].get(metric, 0)) > 1e-9:
            raise ValueError(f"summary.{name} is not derivable from metrics.{metric}")
    if record.get("topDistricts"):
        out["t"] = [[row[f] for f in TOP_FIELDS] for row in record["topDistricts"]]
    keys["metrics"].update(record["metrics"])
    keys["display"].update(record.get("displayMetrics", {}))
    keys["cells"].update(record.get("suppressedCells", {}))
    keys["cells"].update(record.get("approximatedCells", {}))
    return out


def _expand_record(record: dict, keys: dict) -> dict:
    metrics = {k: record.get("m", {}).get(k, 0) for k in keys["metrics"]}
    display = {k: metrics[k] for k in keys["display"]}
    display.update(record.get("d", {}))
    return {
        "metrics": metrics,
        "displayMetrics": display,
        "approximatedCells": {k: record.get("a", {}).get(k, 0) for k in keys["cells"]},
        "suppressedCells": {k: record.get("s", {}).get(k, 0) for k in keys["cells"]},
        "summary": {name: metrics.get(metric, 0) for name, metric in SUMMARY_FROM_METRIC.items()},
        "topDistricts": [dict(zip(TOP_FIELDS, row)) for row in record.get("t", [])],
    }


def compact(payload: dict) -> dict:
    if payload.get("format") == FORMAT_VERSION:
        return payload
    out = copy.deepcopy(payload)
    keys = {"metrics": {}, "display": {}, "cells": {}}
    for dataset in out["datasets"].values():
        for source in dataset["sources"].values():
            for item in source["items"].values():
                item["years"] = {y: _compact_record(r, keys) for y, r in item["years"].items()}
            source["stateTotals"] = {y: _compact_record(r, keys) for y, r in source["stateTotals"].items()}
    out["format"] = FORMAT_VERSION
    out["recordKeys"] = {k: list(v) for k, v in keys.items()}
    return out


def expand(payload: dict) -> dict:
    if payload.get("format") != FORMAT_VERSION:
        return payload
    out = copy.deepcopy(payload)
    keys = out.pop("recordKeys")
    out.pop("format")
    for dataset in out["datasets"].values():
        for source in dataset["sources"].values():
            for item in source["items"].values():
                item["years"] = {y: _expand_record(r, keys) for y, r in item["years"].items()}
            source["stateTotals"] = {y: _expand_record(r, keys) for y, r in source["stateTotals"].items()}
    return out


def canonical(payload: dict) -> dict:
    """Full payload with display copies that only differ by float noise removed.

    Used by the validator so the original and compact files compare as equal.
    """
    return expand(compact(payload))
