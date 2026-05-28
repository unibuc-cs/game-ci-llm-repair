import json
import re
import unittest
from pathlib import Path

import dashboard


ROOT = Path(__file__).resolve().parents[1]


class DashboardTests(unittest.TestCase):
    def test_dashboard_embeds_report_cases(self):
        report = json.loads((ROOT / "outputs" / "demo_report.json").read_text(encoding="utf-8"))
        html = dashboard.build_html(report)

        self.assertIn("Governed Repair Dashboard", html)
        self.assertIn("A-CrosswalkDesync", html)
        self.assertIn("B-BrakeOscillation", html)
        self.assertIn("C-FourWayDeadlock", html)

        match = re.search(
            r'<script id="report-data" type="application/json">(.*?)</script>',
            html,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        embedded = json.loads(match.group(1))
        self.assertEqual(embedded["summary"]["cases"], 4)


if __name__ == "__main__":
    unittest.main()
