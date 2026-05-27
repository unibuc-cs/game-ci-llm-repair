import unittest
from pathlib import Path
from unittest.mock import patch

import orchestrator


ROOT = Path(__file__).resolve().parents[1]


class OrchestratorDemoTests(unittest.TestCase):
    def setUp(self):
        self.cases = orchestrator.load_json(ROOT / "data" / "synthetic_cases.json")
        self.policies = orchestrator.load_json(ROOT / "config" / "policies.json")
        self.architectures = orchestrator.load_json(ROOT / "config" / "architecture_cards.json")

    def test_d0_routes_representative_cases(self):
        routes = {}
        for case in self.cases:
            arch = self.architectures[case["architecture_card"]]
            routes[case["case_id"]] = orchestrator.diagnosis_d0(case, arch).start_level

        self.assertEqual(routes["A-CrosswalkDesync"], "T1")
        self.assertEqual(routes["B-BrakeOscillation"], "T2")
        self.assertEqual(routes["C-FourWayDeadlock"], "T3")

    def test_end_to_end_demo_statuses(self):
        results = [
            orchestrator.run_case(case, self.policies, self.architectures)
            for case in self.cases
        ]
        by_case = {result.case_id: result for result in results}

        self.assertEqual(by_case["A-CrosswalkDesync"].status, "accepted")
        self.assertEqual(by_case["B-BrakeOscillation"].status, "accepted")
        self.assertEqual(by_case["C-FourWayDeadlock"].status, "partial")
        self.assertEqual(by_case["B-BrakeOscillation"].attempts, 2)
        self.assertEqual(by_case["C-FourWayDeadlock"].last_failing_gate, "invariants")

    def test_replay_runner_applies_real_patches_and_gates(self):
        gate_runner = orchestrator.ReplayProjectGateRunner(
            workspace_root=ROOT,
            trials_root=Path("outputs/test_replay_trials"),
            timeout_s=60,
        )
        results = [
            orchestrator.run_case(
                case,
                self.policies,
                self.architectures,
                gate_runner=gate_runner,
            )
            for case in self.cases
        ]
        by_case = {result.case_id: result for result in results}

        self.assertEqual(by_case["A-CrosswalkDesync"].status, "accepted")
        self.assertEqual(by_case["B-BrakeOscillation"].status, "accepted")
        self.assertEqual(by_case["C-FourWayDeadlock"].status, "partial")
        self.assertEqual(by_case["C-FourWayDeadlock"].last_failing_gate, "invariants")

    def test_permission_gate_rejects_disallowed_visual_edits_before_t3(self):
        case = next(item for item in self.cases if item["case_id"] == "C-FourWayDeadlock")
        arch = self.architectures[case["architecture_card"]]
        policy = self.policies["T2"]
        candidate = {
            "patch_id": "bad-visual-edit",
            "modified_files": ["Content/Blueprints/BP_IntersectionController.uasset.json"],
            "requires_visual_graph_edit": True,
            "gate_results": {"build": {"ok": True, "metrics": {}}},
        }

        outcome = orchestrator.run_gate("build", candidate, policy, arch)
        self.assertFalse(outcome.ok)
        self.assertIn("outside the active file allowlist", outcome.message)

    def test_openai_provider_defaults_to_gpt_55_and_requires_key(self):
        provider = orchestrator.OpenAIPatchProvider()
        self.assertEqual(provider.model, "gpt-5.5")

        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "OPENAI_API_KEY"):
                provider.propose(
                    case=self.cases[0],
                    level="T1",
                    attempt=1,
                    prompt="prompt",
                    symptom={},
                    policy={"prompt": {"temperature": 0.0}},
                    arch={},
                )


if __name__ == "__main__":
    unittest.main()
