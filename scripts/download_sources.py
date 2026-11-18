from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.links.append(href)


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "EndSaR-Interactive-Map/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def looks_like_cepi60(url: str) -> bool:
    name = urllib.parse.unquote(urllib.parse.urlparse(url).path.rsplit("/", 1)[-1]).lower()
    return name.endswith(".xlsx") and bool(re.search(r"(cepi.?60|seclusion.*restraint)", name))


def classify_period(url: str) -> str:
    name = urllib.parse.unquote(urllib.parse.urlparse(url).path.rsplit("/", 1)[-1]).lower()
    if re.search(r"q3.?4|q34|final|60c", name):
        return "full_year"
    if "q3" in name:
        return "q3"
    if "q2" in name:
        return "q2"
    if "q1" in name:
        return "q1"
    return "unknown"


def school_year_from_url(url: str) -> str | None:
    match = re.search(r"/(20\d{2})-(\d{2})/", url)
    if match:
        return f"{match.group(1)}-20{match.group(2)}"
    name = urllib.parse.unquote(url)
    compact = re.search(r"(?<!\d)(1[7-9]|2\d)(1[8-9]|2\d)(?!\d)", name)
    if compact:
        return f"20{compact.group(1)}-20{compact.group(2)}"
    return None


# CEPI publishes one file per school year and replaces it as the year fills in:
# Q1 (Jan/Feb) -> Q2 that also contains Q1 (May/June) -> final with Q1-Q4 and school-year totals (Aug/Sept).
# Each school year therefore has ONE current source; a later release replaces the earlier one.
PERIOD_RANK = {"q1": 1, "q2": 2, "q3": 3, "full_year": 4}


def is_active(item: dict, publish_periods: list[str]) -> bool:
    return item.get("status") != "superseded" and item["period"] in publish_periods


def plan_catalog_changes(manifest: dict, catalog_urls: list[str], today: str) -> list[dict]:
    """Decide, for every CEPI-60 link on the catalog page, whether it is a new school year,
    a newer release that replaces the current file for its year, or an old link to ignore.
    Changes are applied to the manifest in place and returned for the report."""
    publish = manifest["policy"]["publishPeriods"]
    known = {item["url"] for item in manifest["sources"]}
    changes = []
    for url in dict.fromkeys(catalog_urls):
        if url in known or not looks_like_cepi60(url):
            continue
        year, period = school_year_from_url(url), classify_period(url)
        if not year or period not in PERIOD_RANK:
            changes.append({"action": "needs-review", "url": url, "schoolYear": year, "period": period, "reason": "school year or reporting period could not be read from the file name"})
            continue
        current = [item for item in manifest["sources"] if item["schoolYear"] == year and is_active(item, publish)]
        current = max(current, key=lambda item: PERIOD_RANK.get(item["period"], 0)) if current else None
        entry = {"schoolYear": year, "period": period, "status": "review", "importedOn": today, "url": url}
        if current is None:
            manifest["sources"].append(entry)
            changes.append({"action": "add-school-year", **entry})
        elif PERIOD_RANK[period] >= PERIOD_RANK.get(current["period"], 0):
            current["status"] = "superseded"
            current["supersededOn"] = today
            current["supersededBy"] = url
            manifest["sources"].append(entry)
            changes.append({"action": "replace", "replaces": current["url"], **entry})
        else:
            changes.append({"action": "ignored-older-release", "url": url, "schoolYear": year, "period": period, "current": current["url"]})
        known.add(url)
    manifest["sources"] = sorted(manifest["sources"], key=lambda item: (item["schoolYear"], PERIOD_RANK.get(item["period"], 0), item["url"]))
    return changes


def main():
    parser = argparse.ArgumentParser(description="Download the current CEPI source for each school year and detect new releases.")
    parser.add_argument("--manifest", type=Path, default=Path("data/sources.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/sources"))
    parser.add_argument("--report", type=Path, default=Path("build/source-report.json"))
    parser.add_argument("--update-manifest", action="store_true", help="Record new school years and replacement releases (as review entries).")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    publish = manifest["policy"]["publishPeriods"]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    page = fetch(manifest["catalogUrl"]).decode("utf-8", errors="replace")
    links = LinkParser()
    links.feed(page)
    catalog_urls = [urllib.parse.urljoin(manifest["catalogUrl"], href) for href in links.links]
    preview = json.loads(json.dumps(manifest))
    changes = plan_catalog_changes(preview if not args.update_manifest else manifest, catalog_urls, datetime.now(timezone.utc).date().isoformat())
    if args.update_manifest and any(change["action"] in {"add-school-year", "replace"} for change in changes):
        args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    downloaded, active_names = [], set()
    for item in manifest["sources"]:
        if not is_active(item, publish):
            continue
        payload = fetch(item["url"])
        if payload[:2] != b"PK":
            raise ValueError(f"Downloaded source is not an XLSX file: {item['url']}")
        filename = urllib.parse.unquote(item["url"].rsplit("/", 1)[-1])
        (args.output_dir / filename).write_bytes(payload)
        active_names.add(filename)
        downloaded.append({**item, "filename": filename, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()})
    # Files replaced by a newer release are moved aside so they are never combined twice.
    for path in args.output_dir.glob("*.xlsx"):
        if path.name not in active_names:
            (args.output_dir / "superseded").mkdir(exist_ok=True)
            path.replace(args.output_dir / "superseded" / path.name)

    report = {
        "downloaded": downloaded,
        "catalogChanges": changes,
        "unapprovedCandidates": [c for c in changes if c["action"] in {"needs-review", "add-school-year", "replace"} and not args.update_manifest],
        "reviewSources": [item for item in manifest["sources"] if item.get("status") == "review"],
        "manifestUpdated": bool(args.update_manifest and any(c["action"] in {"add-school-year", "replace"} for c in changes)),
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"downloaded": len(downloaded), "catalogChanges": [c["action"] for c in changes]}))


if __name__ == "__main__":
    main()
