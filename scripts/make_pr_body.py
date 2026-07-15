import json
from pathlib import Path


source = json.loads(Path("reports/source-report.json").read_text(encoding="utf-8"))
validation = json.loads(Path("reports/validation-report.json").read_text(encoding="utf-8"))
downloads = source.get("downloaded", [])
candidates = source.get("unapprovedCandidates", [])
review_sources = source.get("reviewSources", [])

lines = [
    "## Automated CEPI data update",
    "",
    f"- Validation: **{validation['status']}**",
    f"- Published years: {', '.join(validation['years'])}",
    f"- Approved source files downloaded: {len(downloads)}",
    f"- Sources requiring period/status review: {len(review_sources)}",
    f"- Regression differences: {validation['differenceCount']}",
    "",
]
if review_sources:
    lines.extend(["### Sources requiring review", ""])
    for item in review_sources:
        lines.append(f"- `{item.get('schoolYear') or 'unknown year'}` / `{item.get('period')}`: {item['url']}")
    lines.append("")
lines.extend([
    "### Review guidance",
    "",
    "Confirm that any new reporting period is correctly classified before merging. Quarterly files are recorded for review but are not published as full-year map data. The live site changes only after this pull request is merged.",
])
Path("build/pr-body.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
