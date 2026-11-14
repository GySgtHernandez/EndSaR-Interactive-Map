from __future__ import annotations

import argparse
import os
import re
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

import openpyxl
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent / "data" / "sources"
OUTPUT_DIR = SCRIPT_DIR.parent / "build"
OUTPUT_FILE = OUTPUT_DIR / "CEPI_Seclusion_Restraint_Combined.xlsx"

SOURCE_EXT = ".xlsx"
EXCLUDE_PREFIXES = ("~$",)
EXCLUDE_NAMES = {OUTPUT_FILE.name}


DISTRICT_COLUMNS = [
    "Source File",
    "Source Sheet",
    "School Year",
    "Period",
    "Entity Level",
    "ISD Code",
    "ISD Name",
    "District Code",
    "District Name",
    "Students with Disabilities Reported as Secluded or Restrained",
    "Total Seclusions of Students with Disabilities",
    "Total Restraints of Students with Disabilities",
    "Students without Disabilities Reported as Secluded or Restrained",
    "Total Seclusions of Students without Disabilities",
    "Total Restraints of Students without Disabilities",
]

ISD_COLUMNS = [
    "Source File",
    "Source Sheet",
    "School Year",
    "Period",
    "Entity Level",
    "ISD Code",
    "ISD Name",
    "Students with Disabilities Reported as Secluded or Restrained",
    "Total Seclusions of Students with Disabilities",
    "Total Restraints of Students with Disabilities",
    "Students without Disabilities Reported as Secluded or Restrained",
    "Total Seclusions of Students without Disabilities",
    "Total Restraints of Students without Disabilities",
]


def clean_value(value):
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return value


def is_end_marker(value) -> bool:
    return isinstance(value, str) and value.strip().lower().replace(" ", "") == "endofrow"


def source_files() -> list[Path]:
    return sorted(
        path
        for path in BASE_DIR.iterdir()
        if path.is_file()
        and path.suffix.lower() == SOURCE_EXT
        and path.name not in EXCLUDE_NAMES
        and not path.name.startswith(EXCLUDE_PREFIXES)
    )


def detect_school_year(wb, fallback_name: str) -> str:
    text_bits = []
    for ws in wb.worksheets[:3]:
        for row in ws.iter_rows(min_row=1, max_row=min(10, ws.max_row), values_only=True):
            text_bits.extend(str(value) for value in row if value is not None)
    text_bits.append(fallback_name)
    haystack = " ".join(text_bits)
    match = re.search(r"(20\d{2})[-–](20\d{2})", haystack)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    compact = re.search(r"\b(\d{2})(\d{2})\b", fallback_name)
    if compact:
        start = int("20" + compact.group(1))
        end = int("20" + compact.group(2))
        if end == start + 1:
            return f"{start}-{end}"
    return "Unknown"


def detect_period(sheet_name: str) -> str:
    normalized = sheet_name.strip().lower()
    if "1st quarter" in normalized:
        return "Q1"
    if "2nd quarter" in normalized:
        return "Q2"
    if "3rd quarter" in normalized:
        return "Q3"
    if "4th quarter" in normalized:
        return "Q4"
    return "Full Year"


def detect_level(sheet_name: str) -> str | None:
    normalized = sheet_name.strip().lower()
    if "district totals" in normalized:
        return "District"
    if "isd totals" in normalized:
        return "ISD"
    return None


def find_header_row(ws) -> int | None:
    for row_index, row in enumerate(
        ws.iter_rows(min_row=1, max_row=min(ws.max_row, 20), max_col=min(ws.max_column, 30), values_only=True),
        start=1,
    ):
        values = [clean_value(value) for value in row]
        labels = {str(value).strip().lower() for value in values if value is not None}
        if "isd code" in labels and "isd name" in labels:
            return row_index
    return None


def normalized_headers(ws, row_index: int) -> list[str]:
    headers = []
    row = next(ws.iter_rows(min_row=row_index, max_row=row_index, values_only=True))
    for value in row:
        value = clean_value(value)
        if is_end_marker(value):
            break
        if value is None:
            if len(headers) >= 8:
                break
            headers.append("")
        else:
            headers.append(str(value))
    while headers and not headers[-1]:
        headers.pop()
    return headers


def extract_totals_sheet(path: Path, ws, school_year: str, level: str, period: str):
    header_row = find_header_row(ws)
    if not header_row:
        return [], None

    headers = normalized_headers(ws, header_row)
    rows = []
    blank_streak = 0
    for values in ws.iter_rows(
        min_row=header_row + 1,
        max_row=ws.max_row,
        max_col=len(headers),
        values_only=True,
    ):
        values = [clean_value(value) for value in values]
        if not any(value is not None for value in values):
            blank_streak += 1
            if blank_streak >= 25:
                break
            continue
        blank_streak = 0
        if values and is_end_marker(values[0]):
            continue
        if level == "District":
            key = values[:4]
            if not any(value is not None for value in key):
                continue
            rows.append([
                path.name,
                ws.title,
                school_year,
                period,
                level,
                values[0] if len(values) > 0 else None,
                values[1] if len(values) > 1 else None,
                values[2] if len(values) > 2 else None,
                values[3] if len(values) > 3 else None,
                values[4] if len(values) > 4 else None,
                values[5] if len(values) > 5 else None,
                values[6] if len(values) > 6 else None,
                values[7] if len(values) > 7 else None,
                values[8] if len(values) > 8 else None,
                values[9] if len(values) > 9 else None,
            ])
        else:
            key = values[:2]
            if not any(value is not None for value in key):
                continue
            rows.append([
                path.name,
                ws.title,
                school_year,
                period,
                level,
                values[0] if len(values) > 0 else None,
                values[1] if len(values) > 1 else None,
                values[2] if len(values) > 2 else None,
                values[3] if len(values) > 3 else None,
                values[4] if len(values) > 4 else None,
                values[5] if len(values) > 5 else None,
                values[6] if len(values) > 6 else None,
                values[7] if len(values) > 7 else None,
            ])

    return rows, headers


def extract_field_definitions(wb, source_file: str, school_year: str):
    definitions = []
    ws = wb["Field Definitions"] if "Field Definitions" in wb.sheetnames else None
    if ws is None:
        return definitions

    header_row = None
    for row_index, row in enumerate(
        ws.iter_rows(min_row=1, max_row=min(ws.max_row, 20), max_col=min(ws.max_column, 8), values_only=True),
        start=1,
    ):
        values = [clean_value(value) for value in row]
        labels = [str(value).strip().lower() for value in values if value is not None]
        if "field name" in labels and "field definition" in labels:
            header_row = row_index
            break
    if not header_row:
        return definitions

    for row in ws.iter_rows(min_row=header_row + 1, max_row=ws.max_row, max_col=3, values_only=True):
        field_name = clean_value(row[0])
        field_definition = clean_value(row[2]) or clean_value(row[1])
        if field_name and field_definition:
            definitions.append([source_file, school_year, field_name, field_definition])
    return definitions


def append_rows(ws, rows):
    for row in rows:
        ws.append(row)


def apply_basic_style(ws, table_name: str | None = None):
    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(color="FFFFFF", bold=True)
    thin = Side(style="thin", color="D9E2F3")
    border = Border(bottom=thin)

    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    max_col = ws.max_column
    max_row = ws.max_row
    if table_name and max_row >= 2 and max_col >= 1:
        ref = f"A1:{get_column_letter(max_col)}{max_row}"
        table = Table(displayName=table_name, ref=ref)
        table.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium2",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )
        ws.add_table(table)

    for col_index in range(1, max_col + 1):
        letter = get_column_letter(col_index)
        max_len = 0
        for cell in ws[letter][: min(max_row, 250)]:
            if cell.value is not None:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[letter].width = min(max(max_len + 2, 12), 48)


def style_readme(ws):
    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 88
    for row in ws.iter_rows():
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    ws["A1"].font = Font(bold=True, size=16, color="1F4E78")
    for cell in ws["A"]:
        cell.font = Font(bold=True)


def main():
    global BASE_DIR, OUTPUT_DIR, OUTPUT_FILE
    parser = argparse.ArgumentParser(description="Normalize CEPI seclusion and restraint workbooks.")
    parser.add_argument("--source-dir", type=Path, default=BASE_DIR)
    parser.add_argument("--output", type=Path, default=OUTPUT_FILE)
    args = parser.parse_args()
    BASE_DIR = args.source_dir.resolve()
    OUTPUT_FILE = args.output.resolve()
    OUTPUT_DIR = OUTPUT_FILE.parent
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    district_rows = []
    isd_rows = []
    source_index = []
    field_definition_rows = []
    seen_definitions = OrderedDict()

    for path in source_files():
        source_wb = load_workbook(path, read_only=True, data_only=True)
        school_year = detect_school_year(source_wb, path.name)
        source_index.append([path.name, school_year, len(source_wb.sheetnames), ", ".join(source_wb.sheetnames)])

        for definition in extract_field_definitions(source_wb, path.name, school_year):
            key = (definition[2], definition[3])
            seen_definitions.setdefault(key, definition)

        for ws in source_wb.worksheets:
            level = detect_level(ws.title)
            if not level:
                continue
            period = detect_period(ws.title)
            rows, headers = extract_totals_sheet(path, ws, school_year, level, period)
            if not rows:
                continue
            source_index.append([path.name, school_year, ws.title, len(rows)])
            if level == "District":
                district_rows.extend(rows)
            else:
                isd_rows.extend(rows)

    field_definition_rows = list(seen_definitions.values())

    wb = Workbook()
    wb.remove(wb.active)

    readme = wb.create_sheet("README")
    readme.append(["CEPI Seclusion and Restraint Combined Workbook", ""])
    readme.append(["Created", datetime.now().strftime("%Y-%m-%d %H:%M")])
    readme.append(["Source folder", str(BASE_DIR)])
    readme.append(["Source files combined", len(source_files())])
    readme.append(["District rows", len(district_rows)])
    readme.append(["ISD rows", len(isd_rows)])
    readme.append(["Notes", "District_All and ISD_All are normalized long-format sheets. Suppressed source values such as <10 are preserved as text. Source_Index lists the original files and extracted tabs."])
    style_readme(readme)

    index = wb.create_sheet("Source_Index")
    append_rows(index, [["Source File", "School Year", "Sheet or File Count", "Sheets or Extracted Row Count"]] + source_index)
    apply_basic_style(index, "SourceIndex")

    district = wb.create_sheet("District_All")
    append_rows(district, [DISTRICT_COLUMNS] + district_rows)
    apply_basic_style(district, "DistrictAll")

    isd = wb.create_sheet("ISD_All")
    append_rows(isd, [ISD_COLUMNS] + isd_rows)
    apply_basic_style(isd, "ISDAll")

    fields = wb.create_sheet("Field_Definitions")
    append_rows(fields, [["Source File", "School Year", "Field Name", "Field Definition"]] + field_definition_rows)
    apply_basic_style(fields, "FieldDefinitions")

    wb.save(OUTPUT_FILE)
    print(OUTPUT_FILE)
    print(f"district_rows={len(district_rows)}")
    print(f"isd_rows={len(isd_rows)}")
    print(f"field_definitions={len(field_definition_rows)}")


if __name__ == "__main__":
    main()
