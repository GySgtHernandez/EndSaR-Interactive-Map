from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path

from openpyxl import load_workbook

from map_data_format import compact


PROJECT = Path(__file__).resolve().parent
ROOT = PROJECT.parent
WORKBOOK = ROOT / "build" / "CEPI_Seclusion_Restraint_Combined.xlsx"
OUTPUT = ROOT / "site" / "map-data.js"
DATASETS = {
    "raw": {"label": "Raw CEPI Data", "sheet": "Raw_CEPI_Data"},
    "approximated": {"label": "Approximated Data", "sheet": "Approximated_Data", "suppression_sheet": "Raw_CEPI_Data"},
}

CEPI_COUNTIES = [
    "Alcona", "Alger", "Allegan", "Alpena", "Antrim", "Arenac", "Baraga", "Barry", "Bay", "Benzie",
    "Berrien", "Branch", "Calhoun", "Cass", "Charlevoix", "Cheboygan", "Chippewa", "Clare", "Clinton",
    "Crawford", "Delta", "Dickinson", "Eaton", "Emmet", "Genesee", "Gladwin", "Gogebic", "Grand Traverse",
    "Gratiot", "Hillsdale", "Houghton", "Huron", "Ingham", "Ionia", "Iosco", "Iron", "Isabella", "Jackson",
    "Kalamazoo", "Kalkaska", "Kent", "Keweenaw", "Lake", "Lapeer", "Leelanau", "Lenawee", "Livingston",
    "Luce", "Mackinac", "Macomb", "Manistee", "Marquette", "Mason", "Mecosta", "Menominee", "Midland",
    "Missaukee", "Monroe", "Montcalm", "Montmorency", "Muskegon", "Newaygo", "Oakland", "Oceana",
    "Ogemaw", "Ontonagon", "Osceola", "Oscoda", "Otsego", "Ottawa", "Presque Isle", "Roscommon",
    "Saginaw", "Sanilac", "Schoolcraft", "Shiawassee", "St. Clair", "St. Joseph", "Tuscola", "Van Buren",
    "Washtenaw", "Wayne", "Wexford",
]

BASE_METRICS = [
    ("swd_students", "Students with disabilities reported as secluded or restrained"),
    ("swd_seclusions", "Total seclusions of students with disabilities"),
    ("swd_restraints", "Total restraints of students with disabilities"),
    ("nonswd_students", "Students without disabilities reported as secluded or restrained"),
    ("nonswd_seclusions", "Total seclusions of students without disabilities"),
    ("nonswd_restraints", "Total restraints of students without disabilities"),
    ("all_events", "Total seclusions and restraints"),
    ("event_student_ratio", "Events per reported student"),
]

SOURCE_METRIC_KEYS = [
    "swd_students",
    "swd_seclusions",
    "swd_restraints",
    "nonswd_students",
    "nonswd_seclusions",
    "nonswd_restraints",
]

DERIVED_METRIC_KEYS = ["all_events", "event_student_ratio"]

YEAR_PATTERN = [
    ("Students with Disabilities Reported as Secluded or Restrained", "swd_students"),
    ("Total Seclusions of Students with Disabilities", "swd_seclusions"),
    ("Total Restraints of Students with Disabilities", "swd_restraints"),
    ("Students without Disabilities Reported as Secluded or Restrained", "nonswd_students"),
    ("Total Seclusions of Students without Disabilities", "nonswd_seclusions"),
    ("Total Restraints of Students without Disabilities", "nonswd_restraints"),
    ("Total Seclusions and Restraints", "all_events"),
    ("Events per Reported Student", "event_student_ratio"),
    ("Suppressed Values", "suppressed_values"),
]


def norm_code(value, width=None) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    try:
        text = str(int(float(text)))
    except ValueError:
        text = "".join(ch for ch in text if ch.isdigit()) or text
        text = text.lstrip("0") or "0" if text.isdigit() else text
    return text.zfill(width) if width and text.isdigit() else text


def num(value) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace(",", "").strip()
    if text.endswith("*"):
        text = text[:-1]
    try:
        return float(text)
    except ValueError:
        return 0.0


def is_suppressed(value) -> bool:
    return isinstance(value, str) and value.strip() == "<10"


def is_partial(value) -> bool:
    return isinstance(value, str) and value.strip().endswith("*")


def display_metric(value):
    if value is None or value == "":
        return "-"
    if is_suppressed(value):
        return "<10"
    if is_partial(value):
        return str(value).strip()
    return num(value)


def display_sum_from_payloads(metrics, keys):
    total = sum(metrics[key]["value"] for key in keys)
    if any(metrics[key]["suppressed"] for key in keys):
        return f"{total:g}*"
    return total


def derived_display_metrics(metrics):
    return {
        "all_students": display_sum_from_payloads(metrics, ["swd_students", "nonswd_students"]),
        "all_seclusions": display_sum_from_payloads(metrics, ["swd_seclusions", "nonswd_seclusions"]),
        "all_restraints": display_sum_from_payloads(metrics, ["swd_restraints", "nonswd_restraints"]),
    }


def load_boundary_ids(filename):
    text = (PROJECT / filename).read_text(encoding="utf-8")
    data = json.loads(text.split("=", 1)[1].strip().rstrip(";"))
    return {str(feature["properties"]["id"]): feature["properties"] for feature in data["features"]}


DISTRICT_BOUNDARY_PROPS = load_boundary_ids("district-boundaries.js")
ISD_BOUNDARY_PROPS = load_boundary_ids("isd-boundaries.js")
REGION_BOUNDARY_PROPS = load_boundary_ids("region-boundaries.js")
COUNTY_BOUNDARY_PROPS = load_boundary_ids("county-boundaries.js")


def empty_metrics():
    return {key: 0.0 for key, _ in BASE_METRICS}


def empty_year_data():
    return {
        "metrics": empty_metrics(),
        "displayMetrics": {},
        "approximatedCells": {key: 0 for key, _ in BASE_METRICS},
        "suppressedCells": {key: 0 for key, _ in BASE_METRICS},
        "summary": {},
        "topDistricts": [],
    }


def add_summary(year_data):
    m = year_data["metrics"]
    student_total = m["swd_students"] + m["nonswd_students"]
    seclusion_total = m["swd_seclusions"] + m["nonswd_seclusions"]
    restraint_total = m["swd_restraints"] + m["nonswd_restraints"]
    combined_event_total = seclusion_total + restraint_total
    m["all_students"] = student_total
    m["all_seclusions"] = seclusion_total
    m["all_restraints"] = restraint_total
    m["all_events"] = combined_event_total
    m["event_student_ratio"] = combined_event_total / student_total if student_total else 0.0
    if not year_data["displayMetrics"]:
        year_data["displayMetrics"] = {key: m.get(key, 0.0) for key, _ in BASE_METRICS}
    year_data["summary"] = {
        "swd_total": m["swd_students"],
        "nonswd_total": m["nonswd_students"],
        "student_total": student_total,
        "seclusion_total": seclusion_total,
        "restraint_total": restraint_total,
        "combined_event_total": combined_event_total,
    }


def finalized_item(item):
    for year_data in item["years"].values():
        add_summary(year_data)
        year_data["topDistricts"] = sorted(year_data["topDistricts"], key=lambda row: row["total"], reverse=True)[:8]
        for key, value in list(year_data["metrics"].items()):
            year_data["metrics"][key] = round(value, 4)
        for key, value in list(year_data["summary"].items()):
            year_data["summary"][key] = round(value, 4)
    return item


def district_county_id(district_code):
    code = norm_code(district_code)
    if not code.isdigit():
        return ""
    county_code = int(code) // 1000
    county_name = CEPI_COUNTIES[county_code - 1] if 1 <= county_code <= len(CEPI_COUNTIES) else ""
    for fips, props in COUNTY_BOUNDARY_PROPS.items():
        if props.get("cepiCode") == county_code:
            return fips
    return ""


def make_item(key, label, geography_label, name, item_type, years, **extra):
    return {
        "id": key,
        "name": name,
        "type": item_type,
        "label": label,
        "geographyLabel": geography_label,
        "districtCount": 0,
        "years": {year: empty_year_data() for year in years},
        **extra,
    }


def add_metrics(target, year, metrics, top_district=None):
    year_data = target["years"][year]
    for key in ["swd_students", "swd_seclusions", "swd_restraints", "nonswd_students", "nonswd_seclusions", "nonswd_restraints"]:
        year_data["metrics"][key] += metrics[key]
    if top_district and top_district["total"] > 0:
        year_data["topDistricts"].append(top_district)


def load_rows(sheet_name, suppression_sheet_name=None):
    wb = load_workbook(WORKBOOK, read_only=True, data_only=True)
    ws = wb[sheet_name]
    suppression_ws = wb[suppression_sheet_name or sheet_name]
    headers = [cell.value for cell in ws[1]]
    years = []
    year_columns = {}
    for index, header in enumerate(headers):
        if not header or index < 6:
            continue
        year, label = str(header).split(" ", 1)
        if year not in years:
            years.append(year)
            year_columns[year] = {}
        for expected_label, key in YEAR_PATTERN:
            if label == expected_label:
                year_columns[year][key] = index
                break

    rows = []
    state_years = {}
    suppression_rows = suppression_ws.iter_rows(min_row=2, values_only=True)
    for row, suppression_row in zip(ws.iter_rows(min_row=2, values_only=True), suppression_rows):
        district_code = norm_code(row[4], 5)
        isd_code = norm_code(row[2], 2)
        region = norm_code(row[0])
        row_years = {}
        for year in years:
            row_years[year] = {}
            source_suppressed = {}
            for key in SOURCE_METRIC_KEYS:
                source_suppressed[key] = is_suppressed(suppression_row[year_columns[year][key]])
            suppressed_total_col = year_columns[year].get("suppressed_values")
            suppressed_total = int(num(suppression_row[suppressed_total_col])) if suppressed_total_col is not None else sum(1 for value in source_suppressed.values() if value)
            for key, col in year_columns[year].items():
                if key == "suppressed_values":
                    continue
                raw_value = row[col]
                row_years[year][key] = {
                    "value": num(raw_value),
                    "display": display_metric(raw_value),
                    "suppressed": is_suppressed(raw_value),
                    "approximated": source_suppressed.get(key, False),
                }
            for key in DERIVED_METRIC_KEYS:
                row_years[year][key]["suppressedCount"] = suppressed_total
                row_years[year][key]["approximatedCount"] = suppressed_total
            row_years[year]["all_events"]["approximated"] = suppressed_total > 0
            row_years[year]["event_student_ratio"]["approximated"] = suppressed_total > 0
        if district_code == "00000" or str(row[5] or "").strip().lower() == "state total":
            state_years = row_years
            continue
        if not district_code:
            continue
        rows.append({
            "region": region,
            "entityLevel": row[1],
            "isdCode": isd_code,
            "isdName": row[3] or "",
            "districtCode": district_code,
            "districtName": row[5] or "",
            "years": row_years,
        })
    return years, rows, state_years


def build_sources(sheet_name, suppression_sheet_name=None):
    years, rows, state_years = load_rows(sheet_name, suppression_sheet_name)
    sources = {
        "district": {"key": "district", "label": "District data", "geographyLabel": "District", "items": {}, "years": [{"year": year} for year in years], "stateTotals": {year: empty_year_data() for year in years}, "unmatched": []},
        "isd": {"key": "isd", "label": "ISD data", "geographyLabel": "ISD", "items": {}, "years": [{"year": year} for year in years], "stateTotals": {year: empty_year_data() for year in years}, "unmatched": []},
        "isd_entity": {"key": "isd_entity", "label": "ISD entity only", "geographyLabel": "ISD", "items": {}, "years": [{"year": year} for year in years], "stateTotals": {year: empty_year_data() for year in years}, "unmatched": []},
        "region": {"key": "region", "label": "Region data", "geographyLabel": "Region", "items": {}, "years": [{"year": year} for year in years], "stateTotals": {year: empty_year_data() for year in years}, "unmatched": []},
        "region_entity": {"key": "region_entity", "label": "Region ISD entities only", "geographyLabel": "Region", "items": {}, "years": [{"year": year} for year in years], "stateTotals": {year: empty_year_data() for year in years}, "unmatched": []},
        "county": {"key": "county", "label": "County data", "geographyLabel": "County", "items": {}, "years": [{"year": year} for year in years], "stateTotals": {year: empty_year_data() for year in years}, "unmatched": []},
    }

    for fips, props in COUNTY_BOUNDARY_PROPS.items():
        sources["county"]["items"][fips] = make_item(fips, "County data", "County", props.get("name") or props.get("NAME") or fips, "County", years, fips=fips, cepiCode=props.get("cepiCode"))
    for isd_id, props in ISD_BOUNDARY_PROPS.items():
        sources["isd"]["items"][isd_id] = make_item(isd_id, "ISD data", "ISD", props.get("name") or isd_id, "ISD", years, region=props.get("region"))
        sources["isd_entity"]["items"][isd_id] = make_item(isd_id, "ISD entity only", "ISD", props.get("name") or isd_id, "ISD", years, region=props.get("region"))
    for region_id, props in REGION_BOUNDARY_PROPS.items():
        sources["region"]["items"][region_id] = make_item(region_id, "Region data", "Region", props.get("name") or f"Region {region_id}", "Region", years, isdCount=props.get("isdCount", 0))
        sources["region_entity"]["items"][region_id] = make_item(region_id, "Region ISD entities only", "Region", props.get("name") or f"Region {region_id}", "Region", years, isdCount=props.get("isdCount", 0))

    for row in rows:
        district_id = row["districtCode"]
        if district_id not in DISTRICT_BOUNDARY_PROPS:
            sources["district"]["unmatched"].append({"code": district_id, "name": row["districtName"]})
        sources["district"]["items"].setdefault(
            district_id,
            make_item(district_id, "District data", "District", row["districtName"], "District", years, isdCode=row["isdCode"], isdName=row["isdName"], region=row["region"]),
        )
        sources["district"]["items"][district_id]["districtCount"] = 1

        isd_id = row["isdCode"]
        region_id = row["region"]
        county_id = district_county_id(district_id)
        is_isd_entity = district_id == f"{int(isd_id):02d}000" if isd_id.isdigit() else False

        if isd_id in sources["isd"]["items"]:
            sources["isd"]["items"][isd_id]["districtCount"] += 1
        if region_id in sources["region"]["items"]:
            sources["region"]["items"][region_id]["districtCount"] += 1
        if county_id in sources["county"]["items"]:
            sources["county"]["items"][county_id]["districtCount"] += 1
        if is_isd_entity:
            if isd_id in sources["isd_entity"]["items"]:
                sources["isd_entity"]["items"][isd_id]["districtCount"] += 1
            if region_id in sources["region_entity"]["items"]:
                sources["region_entity"]["items"][region_id]["districtCount"] += 1

        for year, metrics in row["years"].items():
            metric_values = {key: payload["value"] for key, payload in metrics.items()}
            metric_displays = {key: payload["display"] for key, payload in metrics.items()}
            metric_displays.update(derived_display_metrics(metrics))
            suppressed_counts = {key: payload.get("suppressedCount", 1 if payload["suppressed"] else 0) for key, payload in metrics.items()}
            approximated_counts = {key: payload.get("approximatedCount", 1 if payload["approximated"] else 0) for key, payload in metrics.items()}
            top_district = {
                "district": row["districtName"],
                "code": district_id,
                "total": round(metric_values["all_events"], 4),
                "suppressed": sum(suppressed_counts.values()),
            }
            add_metrics(sources["district"]["items"][district_id], year, metric_values)
            sources["district"]["items"][district_id]["years"][year]["displayMetrics"] = metric_displays
            for metric_key, count in suppressed_counts.items():
                sources["district"]["items"][district_id]["years"][year]["suppressedCells"][metric_key] += count
            for metric_key, count in approximated_counts.items():
                sources["district"]["items"][district_id]["years"][year]["approximatedCells"][metric_key] += count
            if isd_id in sources["isd"]["items"]:
                add_metrics(sources["isd"]["items"][isd_id], year, metric_values, top_district)
                for metric_key, count in suppressed_counts.items():
                    sources["isd"]["items"][isd_id]["years"][year]["suppressedCells"][metric_key] += count
                for metric_key, count in approximated_counts.items():
                    sources["isd"]["items"][isd_id]["years"][year]["approximatedCells"][metric_key] += count
            if region_id in sources["region"]["items"]:
                add_metrics(sources["region"]["items"][region_id], year, metric_values, top_district)
                for metric_key, count in suppressed_counts.items():
                    sources["region"]["items"][region_id]["years"][year]["suppressedCells"][metric_key] += count
                for metric_key, count in approximated_counts.items():
                    sources["region"]["items"][region_id]["years"][year]["approximatedCells"][metric_key] += count
            if county_id in sources["county"]["items"]:
                add_metrics(sources["county"]["items"][county_id], year, metric_values, top_district)
                for metric_key, count in suppressed_counts.items():
                    sources["county"]["items"][county_id]["years"][year]["suppressedCells"][metric_key] += count
                for metric_key, count in approximated_counts.items():
                    sources["county"]["items"][county_id]["years"][year]["approximatedCells"][metric_key] += count
            if is_isd_entity:
                if isd_id in sources["isd_entity"]["items"]:
                    add_metrics(sources["isd_entity"]["items"][isd_id], year, metric_values, top_district)
                    for metric_key, count in suppressed_counts.items():
                        sources["isd_entity"]["items"][isd_id]["years"][year]["suppressedCells"][metric_key] += count
                    for metric_key, count in approximated_counts.items():
                        sources["isd_entity"]["items"][isd_id]["years"][year]["approximatedCells"][metric_key] += count
                if region_id in sources["region_entity"]["items"]:
                    add_metrics(sources["region_entity"]["items"][region_id], year, metric_values, top_district)
                    for metric_key, count in suppressed_counts.items():
                        sources["region_entity"]["items"][region_id]["years"][year]["suppressedCells"][metric_key] += count
                    for metric_key, count in approximated_counts.items():
                        sources["region_entity"]["items"][region_id]["years"][year]["approximatedCells"][metric_key] += count

    for source in sources.values():
        for item in source["items"].values():
            finalized_item(item)
        for year in years:
            totals = source["stateTotals"][year]
            for item in source["items"].values():
                for key in ["swd_students", "swd_seclusions", "swd_restraints", "nonswd_students", "nonswd_seclusions", "nonswd_restraints"]:
                    totals["metrics"][key] += item["years"][year]["metrics"][key]
                for key in totals["suppressedCells"]:
                    totals["suppressedCells"][key] += item["years"][year]["suppressedCells"].get(key, 0)
                for key in totals["approximatedCells"]:
                    totals["approximatedCells"][key] += item["years"][year]["approximatedCells"].get(key, 0)
            if source["key"] not in {"isd_entity", "region_entity"} and year in state_years:
                state_metrics = {key: payload["value"] for key, payload in state_years[year].items()}
                state_displays = {key: payload["display"] for key, payload in state_years[year].items()}
                for key in SOURCE_METRIC_KEYS:
                    totals["metrics"][key] = state_metrics.get(key, totals["metrics"].get(key, 0))
                totals["displayMetrics"] = state_displays
            add_summary(totals)
            for key, value in list(totals["metrics"].items()):
                totals["metrics"][key] = round(value, 4)
            for key, value in list(totals["summary"].items()):
                totals["summary"][key] = round(value, 4)
    return sources, years


def main():
    global WORKBOOK, OUTPUT
    parser = argparse.ArgumentParser(description="Generate the browser map data artifact.")
    parser.add_argument("--workbook", type=Path, default=WORKBOOK)
    parser.add_argument("--output", type=Path, help="Optional legacy map-data.js (full format) for debugging.")
    parser.add_argument("--json-output", type=Path, default=ROOT / "site" / "data" / "map-data.json", help="Compact JSON loaded by the map page.")
    args = parser.parse_args()
    WORKBOOK = args.workbook.resolve()
    OUTPUT = args.output.resolve() if args.output else None
    datasets = {}
    years = []
    for key, config in DATASETS.items():
        sources, years = build_sources(config["sheet"], config.get("suppression_sheet"))
        datasets[key] = {
            "key": key,
            "label": config["label"],
            "sheet": config["sheet"],
            "sources": sources,
        }
    metrics = [{"key": key, "label": label} for key, label in BASE_METRICS]
    metadata = {
        "title": "EndSaR Data Map",
        "sourceWorkbook": WORKBOOK.name,
        "sheets": {key: config["sheet"] for key, config in DATASETS.items()},
        "years": years,
        "suppressionNote": "Approximated_Data uses reconciled suppressed-value estimates from ISD totals where available.",
    }
    payload = {"datasets": datasets, "defaultDataset": "approximated", "metrics": metrics, "metadata": metadata}
    if OUTPUT:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(
            "const MAP_DATASETS = " + json.dumps(datasets, indent=2)
            + ";\nconst DEFAULT_DATASET = \"approximated\";\nconst MAP_SOURCES = MAP_DATASETS[DEFAULT_DATASET].sources"
            + ";\nconst METRICS = " + json.dumps(metrics, indent=2)
            + ";\nconst MAP_METADATA = " + json.dumps(metadata, indent=2) + ";\n",
            encoding="utf-8",
        )
        print(OUTPUT)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(compact(payload), separators=(",", ":")) + "\n", encoding="utf-8")
    print(args.json_output)
    for dataset_key, dataset in datasets.items():
        print(dataset_key, dataset["sheet"])
        for key, source in dataset["sources"].items():
            print(" ", key, len(source["items"]), "items", len(source["unmatched"]), "unmatched")


if __name__ == "__main__":
    main()
