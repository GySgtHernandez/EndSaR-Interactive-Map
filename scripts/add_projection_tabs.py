from __future__ import annotations

import argparse
import csv
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = BASE_DIR.parent / "build" / "CEPI_Seclusion_Restraint_Combined.xlsx"
REFERENCE_FILE = BASE_DIR.parent / "data" / "district-roster.csv"
REGION_FILE = BASE_DIR / "isd-code-to-region.txt"

RAW_SHEET = "Raw_CEPI_Data"
APPROX_SHEET = "Approximated_Data"
RANGE_SHEET = "Suppressed_Range_Data"

YEARS = []

IDENTITY_COLUMNS = ["Region", "Entity Level", "ISD Code", "ISD Name", "District Code", "District Name"]

YEAR_HEADER_COLORS = [
    "1F4E78",
    "548235",
    "8064A2",
    "C65911",
    "2F75B5",
    "A64D79",
    "7F6000",
    "385723",
]

YEAR_BODY_COLORS = [
    "D9EAF7",
    "E2F0D9",
    "EADCF8",
    "FCE4D6",
    "DDEBF7",
    "F4CCCC",
    "FFF2CC",
    "E2F0D9",
]

METRICS = [
    ("Students with Disabilities Reported as Secluded or Restrained", "swd_students"),
    ("Total Seclusions of Students with Disabilities", "swd_seclusions"),
    ("Total Restraints of Students with Disabilities", "swd_restraints"),
    ("Students without Disabilities Reported as Secluded or Restrained", "nodis_students"),
    ("Total Seclusions of Students without Disabilities", "nodis_seclusions"),
    ("Total Restraints of Students without Disabilities", "nodis_restraints"),
    ("Total Seclusions and Restraints", "all_events"),
    ("Events per Reported Student", "all_ratio"),
]

BASE_CEPI_FIELDS = [
    "swd_students",
    "swd_seclusions",
    "swd_restraints",
    "nodis_students",
    "nodis_seclusions",
    "nodis_restraints",
]

EVENT_FIELDS = [
    "swd_seclusions",
    "swd_restraints",
    "nodis_seclusions",
    "nodis_restraints",
]

SUPPRESSED_COUNT_LABEL = "Suppressed Values"

SOURCE_HEADERS = {
    "school_year": "School Year",
    "period": "Period",
    "district_code": "District Code",
    "district_name": "District Name",
    "isd_code": "ISD Code",
    "isd_name": "ISD Name",
    "swd_students": "Students with Disabilities Reported as Secluded or Restrained",
    "swd_seclusions": "Total Seclusions of Students with Disabilities",
    "swd_restraints": "Total Restraints of Students with Disabilities",
    "nodis_students": "Students without Disabilities Reported as Secluded or Restrained",
    "nodis_seclusions": "Total Seclusions of Students without Disabilities",
    "nodis_restraints": "Total Restraints of Students without Disabilities",
}


def norm_code(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    try:
        return str(int(float(text)))
    except ValueError:
        return text.lstrip("0") or "0"


def is_suppressed(value) -> bool:
    return isinstance(value, str) and value.strip() == "<10"


def normalized_text(value) -> str:
    return str(value or "").strip().lower()


def is_state_total_row(row, idx) -> bool:
    return any(
        normalized_text(row[idx.get(header)]) == "state total"
        for header in (SOURCE_HEADERS["isd_name"], SOURCE_HEADERS["district_name"])
        if header in idx
    )


def is_footer_row(row, idx) -> bool:
    footer_values = {"end of table", "end of worksheet"}
    return any(
        normalized_text(row[idx.get(header)]) in footer_values
        for header in (SOURCE_HEADERS["isd_code"], SOURCE_HEADERS["isd_name"], SOURCE_HEADERS["district_code"], SOURCE_HEADERS["district_name"])
        if header in idx
    )


def load_regions():
    regions = {}
    if not REGION_FILE.exists():
        return regions
    for line in REGION_FILE.read_text(encoding="utf-8").splitlines():
        body = line.split("//", 1)[0].strip().rstrip(",")
        if ":" not in body:
            continue
        code, region = body.split(":", 1)
        code = norm_code(code.strip())
        region = region.strip()
        if code and region:
            try:
                regions[code] = int(float(region))
            except ValueError:
                regions[code] = region
    return regions


def as_number(value, suppressed_value=None):
    if is_suppressed(value):
        return suppressed_value
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def format_partial_total(value, suppressed_count):
    if value is None:
        return None
    display = round(value, 4) if isinstance(value, float) and not value.is_integer() else value
    return f"{display:g}*" if suppressed_count else display


def suppressed_count(record):
    if not record:
        return None
    return sum(1 for field in BASE_CEPI_FIELDS if is_suppressed(record.get(field)))


def sum_raw(*values):
    if any(is_suppressed(value) for value in values):
        return "<10"
    nums = [as_number(value) for value in values]
    if any(value is None for value in nums):
        return None
    return sum(nums)


def sum_raw_partial(*values):
    nums = [as_number(value) for value in values if not is_suppressed(value)]
    if any(value is None for value in nums):
        return None
    return format_partial_total(sum(nums), sum(1 for value in values if is_suppressed(value)))


def ratio_raw(numerator_values, denominator_value):
    if any(is_suppressed(value) for value in numerator_values) or is_suppressed(denominator_value):
        return None
    numerator_parts = [as_number(value) for value in numerator_values]
    if any(value is None for value in numerator_parts):
        return None
    numerator = sum(numerator_parts)
    denominator = as_number(denominator_value)
    if not denominator:
        return None
    return numerator / denominator


def ratio_raw_partial(numerator_values, denominator_values):
    numerator_nums = [as_number(value) for value in numerator_values if not is_suppressed(value)]
    denominator_nums = [as_number(value) for value in denominator_values if not is_suppressed(value)]
    if any(value is None for value in numerator_nums) or any(value is None for value in denominator_nums):
        return None
    denominator = sum(denominator_nums)
    if not denominator:
        return None
    suppressed = sum(1 for value in list(numerator_values) + list(denominator_values) if is_suppressed(value))
    return format_partial_total(sum(numerator_nums) / denominator, suppressed)


def sum_approx(*values):
    nums = [as_number(value, 4.5) for value in values]
    if any(value is None for value in nums):
        return None
    return sum(nums)


def ratio_approx(numerator_values, denominator_value):
    numerator = sum_approx(*numerator_values)
    denominator = as_number(denominator_value, 4.5)
    if numerator is None or not denominator:
        return None
    return numerator / denominator


def low_high(value):
    if is_suppressed(value):
        return 1, 9, True
    number = as_number(value)
    if number is None:
        return None, None, False
    return number, number, False


def range_text(low, high, is_ratio=False):
    if low is None or high is None:
        return None
    if abs(low - high) < 0.0000001:
        return round(low, 4) if is_ratio else low
    if is_ratio:
        return f"{low:.4f}-{high:.4f}"
    return f"{low:g}-{high:g}"


def sum_range(*values):
    lows = []
    highs = []
    for value in values:
        low, high, _ = low_high(value)
        if low is None or high is None:
            return None
        lows.append(low)
        highs.append(high)
    return range_text(sum(lows), sum(highs))


def ratio_range(numerator_values, denominator_values):
    numerator_lows = []
    numerator_highs = []
    denominator_lows = []
    denominator_highs = []
    for value in numerator_values:
        low, high, _ = low_high(value)
        if low is None or high is None:
            return None
        numerator_lows.append(low)
        numerator_highs.append(high)
    for value in denominator_values:
        low, high, _ = low_high(value)
        if low is None or high is None:
            return None
        denominator_lows.append(low)
        denominator_highs.append(high)
    denominator_low = sum(denominator_lows)
    denominator_high = sum(denominator_highs)
    if denominator_low <= 0 or denominator_high <= 0:
        return None
    low_ratio = sum(numerator_lows) / denominator_high
    high_ratio = sum(numerator_highs) / denominator_low
    return range_text(low_ratio, high_ratio, is_ratio=True)


def load_roster():
    roster = []
    seen = set()
    with REFERENCE_FILE.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            district_code = row["district_code"]
            district_name = row["district_name"]
            key = norm_code(district_code)
            if not key or key in seen:
                continue
            seen.add(key)
            roster.append({
                "type": row["entity_level"],
                "region": row["region"],
                "code": district_code,
                "name": district_name,
                "key": key,
            })
    return roster


def load_district_data(wb):
    ws = wb["District_All"]
    headers = [cell.value for cell in ws[1]]
    idx = {header: pos for pos, header in enumerate(headers)}
    data = {}
    metadata = {}

    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[idx[SOURCE_HEADERS["period"]]] != "Full Year":
            continue
        year = row[idx[SOURCE_HEADERS["school_year"]]]
        if year not in YEARS:
            continue

        if is_footer_row(row, idx):
            continue

        district_code = row[idx[SOURCE_HEADERS["district_code"]]]
        district_name = row[idx[SOURCE_HEADERS["district_name"]]]
        if is_state_total_row(row, idx):
            key = "0"
            district_name = "State Total"
            district_code = "0"
            entity_level = row[idx["Entity Level"]]
            isd_code = "0"
            isd_name = "State Total"
        elif district_code is None and district_name is None:
            continue
        else:
            key = norm_code(district_code)
            entity_level = row[idx["Entity Level"]]
            isd_code = row[idx[SOURCE_HEADERS["isd_code"]]]
            isd_name = row[idx[SOURCE_HEADERS["isd_name"]]]
        values = {
            field: row[idx[header]]
            for field, header in SOURCE_HEADERS.items()
            if field not in {"school_year", "period"}
        }
        data[(key, year)] = values
        metadata.setdefault(key, {
            "entity_level": entity_level,
            "isd_code": isd_code,
            "isd_name": isd_name,
            "district_code": district_code,
            "district_name": district_name,
        })
    return data, metadata


def load_isd_data(wb):
    ws = wb["ISD_All"]
    headers = [cell.value for cell in ws[1]]
    idx = {header: pos for pos, header in enumerate(headers)}
    data = {}

    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[idx["Period"]] != "Full Year":
            continue
        year = row[idx["School Year"]]
        if year not in YEARS:
            continue
        isd_code = row[idx["ISD Code"]]
        key = norm_code(isd_code)
        data[(key, year)] = {
            "swd_students": row[idx["Students with Disabilities Reported as Secluded or Restrained"]],
            "swd_seclusions": row[idx["Total Seclusions of Students with Disabilities"]],
            "swd_restraints": row[idx["Total Restraints of Students with Disabilities"]],
            "nodis_students": row[idx["Students without Disabilities Reported as Secluded or Restrained"]],
            "nodis_seclusions": row[idx["Total Seclusions of Students without Disabilities"]],
            "nodis_restraints": row[idx["Total Restraints of Students without Disabilities"]],
        }
    return data


def build_reconciled_approx_data(district_data, isd_data):
    adjusted = {key: dict(record) for key, record in district_data.items()}
    fields = [
        "swd_students",
        "swd_seclusions",
        "swd_restraints",
        "nodis_students",
        "nodis_seclusions",
        "nodis_restraints",
    ]

    for year in YEARS:
        isd_keys = sorted({norm_code(record["isd_code"]) for (district_key, row_year), record in district_data.items() if row_year == year})
        for isd_key in isd_keys:
            district_keys = [
                district_key
                for (district_key, row_year), record in district_data.items()
                if row_year == year and norm_code(record["isd_code"]) == isd_key
            ]
            isd_record = isd_data.get((isd_key, year))
            if not isd_record:
                continue

            for field in fields:
                values = [district_data[(district_key, year)].get(field) for district_key in district_keys]
                suppressed_positions = [index for index, value in enumerate(values) if is_suppressed(value)]
                if not suppressed_positions:
                    continue

                isd_total = as_number(isd_record.get(field), 4.5)
                if isd_total is None:
                    continue

                known_sum = sum(as_number(value) for value in values if not is_suppressed(value) and as_number(value) is not None)
                remainder = isd_total - known_sum
                if remainder < 0:
                    remainder = 0
                allocated_value = remainder / len(suppressed_positions)

                for position in suppressed_positions:
                    district_key = district_keys[position]
                    adjusted[(district_key, year)][field] = allocated_value

    for key, record in adjusted.items():
        for field in fields:
            if is_suppressed(record.get(field)):
                record[field] = 4.5
    return adjusted


def compute_values(record, mode):
    if not record:
        return {key: None for _, key in METRICS}

    swd_students = record["swd_students"]
    swd_seclusions = record["swd_seclusions"]
    swd_restraints = record["swd_restraints"]
    nodis_students = record["nodis_students"]
    nodis_seclusions = record["nodis_seclusions"]
    nodis_restraints = record["nodis_restraints"]

    if mode == "raw":
        return {
            "swd_students": swd_students,
            "swd_seclusions": swd_seclusions,
            "swd_restraints": swd_restraints,
            "nodis_students": nodis_students,
            "nodis_seclusions": nodis_seclusions,
            "nodis_restraints": nodis_restraints,
            "all_events": sum_raw_partial(swd_seclusions, swd_restraints, nodis_seclusions, nodis_restraints),
            "all_ratio": ratio_raw_partial(
                [swd_seclusions, swd_restraints, nodis_seclusions, nodis_restraints],
                [swd_students, nodis_students],
            ),
        }
    if mode == "approx":
        all_students = sum_approx(swd_students, nodis_students)
        all_events = sum_approx(swd_seclusions, swd_restraints, nodis_seclusions, nodis_restraints)
        return {
            "swd_students": swd_students,
            "swd_seclusions": swd_seclusions,
            "swd_restraints": swd_restraints,
            "nodis_students": nodis_students,
            "nodis_seclusions": nodis_seclusions,
            "nodis_restraints": nodis_restraints,
            "all_events": all_events,
            "all_ratio": None if not all_students else all_events / all_students,
        }
    return {
        "swd_students": swd_students,
        "swd_seclusions": swd_seclusions,
        "swd_restraints": swd_restraints,
        "nodis_students": nodis_students,
        "nodis_seclusions": nodis_seclusions,
        "nodis_restraints": nodis_restraints,
        "all_events": sum_range(swd_seclusions, swd_restraints, nodis_seclusions, nodis_restraints),
        "all_ratio": ratio_range(
            [swd_seclusions, swd_restraints, nodis_seclusions, nodis_restraints],
            [swd_students, nodis_students],
        ),
    }


def create_projection_sheet(wb, sheet_name, data, metadata, regions, mode):
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]
    ws = wb.create_sheet(sheet_name)

    headers = IDENTITY_COLUMNS[:]
    for year in YEARS:
        headers.extend([f"{year} {label}" for label, _ in METRICS])
        if mode == "raw":
            headers.append(f"{year} {SUPPRESSED_COUNT_LABEL}")
    ws.append(headers)

    for key, meta in metadata.items():
        isd_region_key = norm_code(meta.get("isd_code"))
        if not isd_region_key and str(meta.get("isd_name") or "").strip().lower() == "state total":
            isd_region_key = "0"
        region = regions.get(isd_region_key)
        row = [
            region,
            meta.get("entity_level"),
            meta.get("isd_code"),
            meta.get("isd_name"),
            meta.get("district_code"),
            meta.get("district_name"),
        ]
        for year in YEARS:
            record = data.get((key, year))
            computed = compute_values(record, mode)
            row.extend(computed[key] for _, key in METRICS)
            if mode == "raw":
                row.append(suppressed_count(record))
        ws.append(row)

    style_projection_sheet(ws, mode)


def style_projection_sheet(ws, mode):
    identity_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(color="FFFFFF", bold=True)
    thin = Side(style="thin", color="D9E2F3")
    border = Border(bottom=thin)

    for col_index, cell in enumerate(ws[1], start=1):
        if col_index <= len(IDENTITY_COLUMNS):
            cell.fill = identity_fill
        else:
            year_index = (col_index - len(IDENTITY_COLUMNS) - 1) // len(METRICS)
            cell.fill = PatternFill("solid", fgColor=YEAR_HEADER_COLORS[year_index % len(YEAR_HEADER_COLORS)])
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border

    ws.freeze_panes = "G2"
    ws.auto_filter.ref = ws.dimensions
    ws.sheet_view.showGridLines = False
    ws.sheet_properties.outlinePr.summaryRight = True

    widths = {
        1: 10,
        2: 14,
        3: 12,
        4: 36,
        5: 14,
        6: 38,
    }
    for col in range(1, ws.max_column + 1):
        ws.column_dimensions[get_column_letter(col)].width = widths.get(col, 17)

    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        for cell in row:
            cell.alignment = Alignment(vertical="top")

    year_col_count = len(METRICS) + (1 if mode == "raw" else 0)
    ratio_cols = []
    suppressed_count_cols = []
    for year_index in range(len(YEARS)):
        start = len(IDENTITY_COLUMNS) + (year_index * year_col_count) + 1
        end = start + year_col_count - 1
        year_fill = PatternFill("solid", fgColor=YEAR_BODY_COLORS[year_index % len(YEAR_BODY_COLORS)])
        for col in range(start, end + 1):
            ws.column_dimensions[get_column_letter(col)].outlineLevel = 1
            for cell in ws.iter_cols(min_col=col, max_col=col, min_row=2, max_row=ws.max_row):
                for item in cell:
                    item.fill = year_fill
        ws.column_dimensions.group(
            get_column_letter(start),
            get_column_letter(end),
            outline_level=1,
            hidden=False,
        )
        ratio_cols.append(start + 7)
        if mode == "raw":
            suppressed_count_cols.append(end)
    if mode != "range":
        for col in ratio_cols:
            for cell in ws.iter_cols(min_col=col, max_col=col, min_row=2, max_row=ws.max_row):
                for item in cell:
                    item.number_format = "0.00"
        for col in suppressed_count_cols:
            for cell in ws.iter_cols(min_col=col, max_col=col, min_row=2, max_row=ws.max_row):
                for item in cell:
                    item.number_format = "0"


def main():
    global OUTPUT_FILE, REFERENCE_FILE, REGION_FILE, YEARS, YEAR_HEADER_COLORS, YEAR_BODY_COLORS
    parser = argparse.ArgumentParser(description="Add normalized raw and suppression-approximated projection sheets.")
    parser.add_argument("--workbook", type=Path, default=OUTPUT_FILE)
    parser.add_argument("--roster", type=Path, default=REFERENCE_FILE, help="CSV with entity_level, region, district_code, and district_name columns.")
    parser.add_argument("--regions", type=Path, default=REGION_FILE)
    args = parser.parse_args()
    OUTPUT_FILE = args.workbook.resolve()
    REFERENCE_FILE = args.roster.resolve()
    REGION_FILE = args.regions.resolve()
    wb = load_workbook(OUTPUT_FILE)
    district_ws = wb["District_All"]
    district_headers = [cell.value for cell in district_ws[1]]
    year_col = district_headers.index("School Year")
    YEARS = sorted({str(row[year_col]) for row in district_ws.iter_rows(min_row=2, values_only=True) if row[year_col]})
    if not YEARS:
        raise ValueError("No school years were found in District_All")
    while len(YEAR_HEADER_COLORS) < len(YEARS):
        YEAR_HEADER_COLORS.extend(YEAR_HEADER_COLORS)
        YEAR_BODY_COLORS.extend(YEAR_BODY_COLORS)
    data, metadata = load_district_data(wb)
    isd_data = load_isd_data(wb)
    regions = load_regions()
    reconciled_approx_data = build_reconciled_approx_data(data, isd_data)
    create_projection_sheet(wb, RAW_SHEET, data, metadata, regions, "raw")
    create_projection_sheet(wb, APPROX_SHEET, reconciled_approx_data, metadata, regions, "approx")
    if RANGE_SHEET in wb.sheetnames:
        del wb[RANGE_SHEET]
    wb.save(OUTPUT_FILE)
    print(OUTPUT_FILE)
    for name in [RAW_SHEET, APPROX_SHEET]:
        ws = wb[name]
        print(f"{name}: {ws.max_row - 1} rows x {ws.max_column} columns")


if __name__ == "__main__":
    main()
