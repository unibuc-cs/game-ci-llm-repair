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
                "fixed_ladder",
                "no_arch_card",
            ]
        )

        report = evaluate.run_evaluation(args)
        modes = report["modes"]

        self.assertEqual(modes["governed"]["summary"]["accepted"], 3)
        self.assertEqual(modes["governed"]["summary"]["partial"], 1)
        self.assertGreater(
            modes["fixed_ladder"]["summary"]["attempts"],
            modes["governed"]["summary"]["attempts"],
        )
        self.assertLess(
            modes["no_arch_card"]["summary"]["accepted"],
            modes["governed"]["summary"]["accepted"],
        )


if __name__ == "__main__":
    unittest.main()
