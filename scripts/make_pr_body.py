import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from map_data_format import expand  # noqa: E402


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
PERIOD_NAMES = {"q1": "Q1 release", "q2": "Q2 release (includes Q1)", "q3": "Q3 release", "full_year": "final file (Q1-Q4 and School Year Totals)"}
changes = source.get("catalogChanges", [])
if changes:
    lines.extend(["### What CEPI published", ""])
    for c in changes:
        name = c.get("url", "").rsplit("/", 1)[-1]
        if c["action"] == "add-school-year":
            lines.append(f"- **New school year {c['schoolYear']}**: `{name}` ({PERIOD_NAMES.get(c['period'], c['period'])}). It appears under the quarter menu as provisional until the final file arrives.")
        elif c["action"] == "replace":
            lines.append(f"- **{c['schoolYear']} updated**: `{name}` ({PERIOD_NAMES.get(c['period'], c['period'])}) replaces `{c['replaces'].rsplit('/', 1)[-1]}`.")
        elif c["action"] == "ignored-older-release":
            lines.append(f"- Ignored `{name}`: an older release than the current {c['schoolYear']} file.")
        else:
            lines.append(f"- **Check by hand**: `{name}` ({c.get('reason', 'unrecognized')}). It was not added.")
    lines.append("")
if review_sources:
    lines.extend(["### Sources requiring review", ""])
    for item in review_sources:
        lines.append(f"- `{item.get('schoolYear') or 'unknown year'}` / `{item.get('period')}`: {item['url']}")
    lines.append("")
map_data = expand(json.loads(Path("site/data/map-data.json").read_text(encoding="utf-8")))
totals = map_data["datasets"]["approximated"]["sources"]["district"]["stateTotals"]
lines.extend(["### Statewide totals in the new map data (approximated data)", "", "| School year | Students reported | Seclusions | Restraints | Total incidents |", "|---|---:|---:|---:|---:|"])
for year in map_data["metadata"]["years"]:
    m = totals[year]["metrics"]
    lines.append(f"| {year} | {m['all_students']:,.0f} | {m['all_seclusions']:,.0f} | {m['all_restraints']:,.0f} | {m['all_events']:,.0f} |")
lines.append("")
lines.extend([
    "### Review guidance",
    "",
    "Check that each new file is listed under the right school year and release above. Mid-year releases only change the Q1-Q4 views; School Year Totals change only when a final file is published. The live site changes only after this pull request is merged.",
])
Path("build").mkdir(exist_ok=True)
Path("build/pr-body.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
