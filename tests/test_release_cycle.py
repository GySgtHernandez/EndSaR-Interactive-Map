"""CEPI replaces each school year's file as the year fills in. The manifest must keep exactly one
current file per school year, replace it with newer releases, and add new school years."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from download_sources import is_active, plan_catalog_changes  # noqa: E402

BASE = "https://www.michigan.gov/cepi/-/media/Project/Websites/cepi/MISchoolData"


def manifest():
    return {"catalogUrl": "x", "policy": {"publishPeriods": ["q1", "q2", "q3", "full_year"]}, "sources": [
        {"schoolYear": "2025-2026", "period": "full_year", "status": "final", "url": f"{BASE}/2025-26/26CEPI60-Q34.xlsx"},
    ]}


def current(m):
    out = {}
    for item in m["sources"]:
        if is_active(item, m["policy"]["publishPeriods"]):
            out.setdefault(item["schoolYear"], []).append(item["url"].rsplit("/", 1)[-1])
    return out


class ReleaseCycleTests(unittest.TestCase):
    def test_full_cycle(self):
        m = manifest()
        old_year = f"{BASE}/2025-26/26CEPI60-Q34.xlsx"
        # January: Q1 for a new school year appears -> added.
        changes = plan_catalog_changes(m, [old_year, f"{BASE}/2026-27/27-CEPI-60-Q1.xlsx"], "2027-02-02")
        self.assertEqual([c["action"] for c in changes], ["add-school-year"])
        self.assertEqual(current(m)["2026-2027"], ["27-CEPI-60-Q1.xlsx"])
        # May: CEPI swaps the Q1 file for a Q2 file (which also holds Q1) -> replaces, one current file.
        changes = plan_catalog_changes(m, [old_year, f"{BASE}/2026-27/27-CEPI-60-Q2.xlsx"], "2027-06-01")
        self.assertEqual([c["action"] for c in changes], ["replace"])
        self.assertEqual(current(m)["2026-2027"], ["27-CEPI-60-Q2.xlsx"])
        # If the old Q1 link were still listed, it is ignored (older release).
        changes = plan_catalog_changes(m, [f"{BASE}/2026-27/27-CEPI-60-Q1-v2.xlsx"], "2027-06-08")
        self.assertEqual([c["action"] for c in changes], ["ignored-older-release"])
        # August: final file with Q1-Q4 and school-year totals -> replaces Q2.
        changes = plan_catalog_changes(m, [f"{BASE}/2026-27/27CEPI60-Q34.xlsx"], "2027-09-01")
        self.assertEqual([c["action"] for c in changes], ["replace"])
        self.assertEqual(current(m)["2026-2027"], ["27CEPI60-Q34.xlsx"])
        # Next January: a new school year is added; earlier years stay untouched.
        changes = plan_catalog_changes(m, [f"{BASE}/2027-28/28-CEPI-60-Q1.xlsx"], "2028-02-01")
        self.assertEqual([c["action"] for c in changes], ["add-school-year"])
        self.assertEqual(current(m), {"2025-2026": ["26CEPI60-Q34.xlsx"], "2026-2027": ["27CEPI60-Q34.xlsx"], "2027-2028": ["28-CEPI-60-Q1.xlsx"]})
        # History is kept: superseded entries say when and by what.
        superseded = [i for i in m["sources"] if i.get("status") == "superseded"]
        self.assertEqual(len(superseded), 2)
        self.assertTrue(all(i["supersededBy"] and i["supersededOn"] for i in superseded))

    def test_corrected_final_replaces_final(self):
        m = manifest()
        changes = plan_catalog_changes(m, [f"{BASE}/2025-26/26CEPI60-Q34-revised.xlsx"], "2026-12-01")
        self.assertEqual([c["action"] for c in changes], ["replace"])
        self.assertEqual(current(m)["2025-2026"], ["26CEPI60-Q34-revised.xlsx"])

    def test_unreadable_name_is_flagged_not_published(self):
        m = manifest()
        changes = plan_catalog_changes(m, [f"{BASE}/misc/CEPI60-notes.xlsx"], "2026-12-01")
        self.assertEqual(changes[0]["action"], "needs-review")
        self.assertEqual(len(m["sources"]), 1)


if __name__ == "__main__":
    unittest.main()
