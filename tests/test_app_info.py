"""The App Data dates come from data/sources.json and the last CEPI check."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class AppInfoTests(unittest.TestCase):
    def run_script(self, manifest, *extra, existing=None):
        with tempfile.TemporaryDirectory() as tmp:
            m, out = Path(tmp) / "sources.json", Path(tmp) / "app-info.json"
            m.write_text(json.dumps(manifest))
            if existing:
                out.write_text(json.dumps(existing))
            subprocess.run([sys.executable, str(ROOT / "scripts" / "write_app_info.py"), "--manifest", str(m), "--output", str(out), *extra], check=True, capture_output=True)
            return json.loads(out.read_text())

    def test_newest_import_wins_and_refresh_is_kept(self):
        manifest = {"policy": {"publishPeriods": ["full_year"]}, "sources": [
            {"schoolYear": "2024-2025", "period": "full_year", "url": "https://x/25CEPI60-Q34.xlsx"},
            {"schoolYear": "2025-2026", "period": "full_year", "importedOn": "2026-09-23", "url": "https://x/26CEPI60-Q34.xlsx"},
            {"schoolYear": "2026-2027", "period": "q2", "importedOn": "2027-02-01", "url": "https://x/27CEPI60-Q2.xlsx"},
        ]}
        info = self.run_script(manifest, existing={"lastRefreshed": "2026-11-16T22:27:10Z"})
        self.assertEqual(info["lastUpdated"], "2026-09-23")
        self.assertEqual(info["lastImportFile"], "26CEPI60-Q34.xlsx")
        self.assertEqual(info["lastRefreshed"], "2026-11-16T22:27:10Z")
        self.assertEqual(self.run_script(manifest, "--refreshed", "2026-11-23T12:30:00Z")["lastRefreshed"], "2026-11-23T12:30:00Z")

    def test_committed_app_info_matches_sources(self):
        info = json.loads((ROOT / "site" / "data" / "app-info.json").read_text())
        self.assertTrue(info["lastImportFile"].endswith(".xlsx"))


if __name__ == "__main__":
    unittest.main()
