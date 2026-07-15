import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from download_sources import classify_period, looks_like_cepi60, school_year_from_url
from validate_map_data import summarize


class SourceDiscoveryTests(unittest.TestCase):
    def test_classifies_final_and_quarterly_files(self):
        self.assertEqual(classify_period("https://example/25CEPI60-Q34.xlsx"), "full_year")
        self.assertEqual(classify_period("https://example/26-CEPI-60-Q2.xlsx"), "q2")

    def test_extracts_school_year_from_catalog_path(self):
        self.assertEqual(school_year_from_url("https://example/MISchoolData/2025-26/26-CEPI-60-Q2.xlsx"), "2025-2026")

    def test_rejects_unrelated_workbook(self):
        self.assertFalse(looks_like_cepi60("https://example/School-Safety.xlsx"))


class GeneratedDataTests(unittest.TestCase):
    def test_committed_map_data_is_structurally_readable(self):
        root = Path(__file__).resolve().parent.parent
        summary = summarize(root / "site" / "data" / "map-data.json")
        self.assertGreaterEqual(len(summary["years"]), 8)
        self.assertIn("approximated", summary["datasets"])
        self.assertEqual(summary["datasets"]["approximated"]["county"]["items"], 83)


if __name__ == "__main__":
    unittest.main()
