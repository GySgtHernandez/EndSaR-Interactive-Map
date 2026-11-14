"""Round-trip check: the compact data file shows exactly the same numbers as the full one."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from map_data_format import compact, expand, _shown  # noqa: E402


def shown(record, key):
    value = record["displayMetrics"].get(key, record["metrics"].get(key, 0))
    return value if isinstance(value, str) else _shown(key, value)


def assert_same(test, full, rebuilt):
    for dk, dataset in full["datasets"].items():
        for sk, source in dataset["sources"].items():
            other = rebuilt["datasets"][dk]["sources"][sk]
            pairs = [(source["stateTotals"][y], other["stateTotals"][y]) for y in source["stateTotals"]]
            for item_id, item in source["items"].items():
                twin = other["items"][item_id]
                test.assertEqual({k: v for k, v in item.items() if k != "years"}, {k: v for k, v in twin.items() if k != "years"})
                pairs += [(item["years"][y], twin["years"][y]) for y in item["years"]]
            for a, b in pairs:
                for field in ("metrics", "suppressedCells", "approximatedCells", "summary", "topDistricts"):
                    test.assertEqual(a[field], b[field])
                for key in a["metrics"]:
                    test.assertEqual(shown(a, key), shown(b, key))


class CompactFormatTests(unittest.TestCase):
    def test_synthetic_round_trip(self):
        record = {
            "metrics": {"swd_students": 12.0, "all_events": 30.000000000000004, "event_student_ratio": 2.5, "all_students": 12.0, "all_seclusions": 10.0, "all_restraints": 20.0, "nonswd_students": 0.0},
            "displayMetrics": {"swd_students": "<10", "all_events": 30.000000000000004, "event_student_ratio": 2.5},
            "suppressedCells": {"swd_students": 1, "all_events": 0},
            "approximatedCells": {"swd_students": 0, "all_events": 2},
            "summary": {"swd_total": 12.0, "nonswd_total": 0.0, "student_total": 12.0, "seclusion_total": 10.0, "restraint_total": 20.0, "combined_event_total": 30.000000000000004},
            "topDistricts": [{"district": "Example", "code": "00001", "total": 5, "suppressed": 0}],
        }
        payload = {"datasets": {"raw": {"sources": {"district": {"items": {"1": {"id": "1", "name": "Example", "years": {"2020-2021": record}}}, "stateTotals": {"2020-2021": record}}}}}}
        packed = json.loads(json.dumps(compact(payload)))
        self.assertEqual(packed["format"], 2)
        assert_same(self, payload, expand(packed))

    def test_committed_site_data_expands(self):
        packed = json.loads((ROOT / "site" / "data" / "map-data.json").read_text(encoding="utf-8"))
        full = expand(packed)
        self.assertIn("approximated", full["datasets"])
        self.assertTrue(full["datasets"]["raw"]["sources"]["county"]["stateTotals"])


if __name__ == "__main__":
    unittest.main()
