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


def main():
    parser = argparse.ArgumentParser(description="Download approved CEPI sources and report newly discovered candidates.")
    parser.add_argument("--manifest", type=Path, default=Path("data/sources.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/sources"))
    parser.add_argument("--report", type=Path, default=Path("build/source-report.json"))
    parser.add_argument("--update-manifest", action="store_true", help="Add newly discovered sources as review candidates.")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    approved = {item["url"]: item for item in manifest["sources"]}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    downloaded = []
    for item in manifest["sources"]:
        if item["period"] not in manifest["policy"]["publishPeriods"]:
            continue
        payload = fetch(item["url"])
        if payload[:2] != b"PK":
            raise ValueError(f"Downloaded source is not an XLSX file: {item['url']}")
        filename = urllib.parse.unquote(item['url'].rsplit('/', 1)[-1])
        target = args.output_dir / filename
        target.write_bytes(payload)
        downloaded.append({**item, "filename": filename, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()})

    page = fetch(manifest["catalogUrl"]).decode("utf-8", errors="replace")
    links = LinkParser()
    links.feed(page)
    candidates = []
    for href in links.links:
        url = urllib.parse.urljoin(manifest["catalogUrl"], href)
        if looks_like_cepi60(url) and url not in approved:
            candidates.append({"url": url, "schoolYear": school_year_from_url(url), "period": classify_period(url), "approved": False})

    if args.update_manifest and candidates:
        for candidate in candidates:
            if not candidate["schoolYear"]:
                continue
            manifest["sources"].append({
                "schoolYear": candidate["schoolYear"],
                "period": candidate["period"],
                "status": "review",
                "importedOn": datetime.now(timezone.utc).date().isoformat(),
                "url": candidate["url"],
            })
        manifest["sources"] = sorted(manifest["sources"], key=lambda item: (item["schoolYear"], item["period"], item["url"]))
        args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    report = {
        "downloaded": downloaded,
        "unapprovedCandidates": sorted(candidates, key=lambda x: x["url"]),
        "reviewSources": [item for item in manifest["sources"] if item.get("status") == "review"],
        "manifestUpdated": bool(args.update_manifest and candidates),
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"downloaded": len(downloaded), "unapprovedCandidates": len(candidates)}))


if __name__ == "__main__":
    main()
