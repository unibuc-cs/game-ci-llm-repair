import unittest

import evaluate


class EvaluationTests(unittest.TestCase):
    def test_governed_mode_beats_baselines_on_synthetic_suite(self):
        args = evaluate.build_arg_parser().parse_args(
            [
                "--gate-runner",
                "synthetic",
                "--modes",
                "governed",
                "B0_single_prompt",
                "B1_multi_attempt_prompt",
                "B2_tool_agent",
                "B3_broad_context_agent",
                "fixed_ladder",
                "no_arch_card",
            ]
        )

        report = evaluate.run_evaluation(args)
        modes = report["modes"]

        self.assertEqual(modes["governed"]["summary"]["accepted"], 4)
        self.assertEqual(modes["governed"]["summary"]["partial"], 1)
        self.assertEqual(modes["B0_single_prompt"]["summary"]["accepted"], 1)
        self.assertEqual(modes["B3_broad_context_agent"]["summary"]["accepted"], 1)
        self.assertGreater(
            modes["fixed_ladder"]["summary"]["attempts"],
            modes["governed"]["summary"]["attempts"],
        )
        self.assertGreater(
            modes["B2_tool_agent"]["summary"]["ci_runs"],
            modes["governed"]["summary"]["ci_runs"],
        )
        self.assertLess(
            modes["no_arch_card"]["summary"]["accepted"],
            modes["governed"]["summary"]["accepted"],
        )
        self.assertLess(
            modes["B3_broad_context_agent"]["summary"]["accepted"],
            modes["governed"]["summary"]["accepted"],
        )
        self.assertEqual(len(report["human_supervision"]), 3)
        maintainability = {row["engine"]: row for row in report["maintainability"]}
        self.assertGreaterEqual(maintainability["Unity"]["accepted_patches"], 3)
        self.assertGreaterEqual(maintainability["UE5"]["accepted_patches"], 1)


if __name__ == "__main__":
    unittest.main()
