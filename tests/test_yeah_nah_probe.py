import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from probe_core import build_probe_bundle, build_scoring_oracle_run, load_built_cases, score_probe_run  # noqa: E402


class YeahNahProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.bundle = Path(self.tmp.name) / "probes"
        build_probe_bundle(ROOT, self.bundle, "8" * 40)
        self.cases = [case for case in load_built_cases(self.bundle) if case["suite"] == "yeah-nah-1"]

    def tearDown(self):
        self.tmp.cleanup()

    def test_yeah_nah_suite_has_24_cases(self):
        self.assertEqual(len(self.cases), 24)

    def test_context_paired_nice_one_cases_exist(self):
        ids = {case["id"] for case in self.cases}
        self.assertIn("yeah-nah:literal:nice-one", ids)
        self.assertIn("yeah-nah:sarcasm:nice-one", ids)

    def test_understatement_cases_preserve_high_or_critical_severity(self):
        cases = [case for case in self.cases if case["expected"]["classification"] == "understatement"]
        self.assertGreaterEqual(len(cases), 3)
        self.assertTrue(all(case["expected"]["severity"] in {"high", "critical"} for case in cases))

    def test_banter_cases_are_not_labelled_actual_hostility(self):
        banter = {"banter", "mock_hostility", "affectionate_insult"}
        cases = [case for case in self.cases if case["expected"]["classification"] in banter]
        self.assertTrue(cases)
        self.assertTrue(all(case["expected"]["hostility"] != "actual" for case in cases))

    def test_actual_hostility_controls_exist(self):
        cases = [case for case in self.cases if case["expected"]["hostility"] == "actual"]
        self.assertGreaterEqual(len(cases), 2)

    def test_yeah_nah_and_nah_yeah_have_opposite_intents(self):
        lookup = {case["id"]: case for case in self.cases}
        self.assertEqual(lookup["yeah-nah:yeah-nah:negative"]["expected"]["answer"], "decline")
        self.assertEqual(lookup["yeah-nah:nah-yeah:positive"]["expected"]["answer"], "accept")

    def test_ambiguous_isolated_utterances_remain_uncertain(self):
        uncertain = [case for case in self.cases if case["expected"]["classification"] == "uncertain"]
        self.assertGreaterEqual(len(uncertain), 2)
        self.assertTrue(all(case["expected"]["sarcasm"] == "uncertain" for case in uncertain))

    def test_speaker_confirmed_sarcasm_is_known(self):
        case = next(case for case in self.cases if case["id"] == "yeah-nah:confirmed-sarcasm")
        self.assertEqual(case["expected"]["epistemic_state"], "known")
        self.assertEqual(case["expected"]["sarcasm"], "yes")

    def test_unconfirmed_pragmatic_classifications_remain_inferred(self):
        cases = [case for case in self.cases if case["id"] != "yeah-nah:confirmed-sarcasm"]
        self.assertTrue(all(case["expected"]["epistemic_state"] == "inferred" for case in cases))

    def test_all_yeah_nah_metrics_score_perfectly_on_oracle(self):
        run = build_scoring_oracle_run(self.bundle)
        report = score_probe_run(ROOT, self.bundle, run)
        metrics = report["yeah_nah_1"]
        self.assertEqual(metrics["overall_accuracy"], 1.0)
        self.assertEqual(metrics["sarcasm_precision"], 1.0)
        self.assertEqual(metrics["sarcasm_recall"], 1.0)
        self.assertEqual(metrics["literal_meaning_error_rate"], 0.0)
        self.assertEqual(metrics["banter_misclassification_rate"], 0.0)
        self.assertEqual(metrics["hostility_false_positive_rate"], 0.0)
        self.assertEqual(metrics["understatement_severity_preservation_rate"], 1.0)
        self.assertEqual(metrics["confidence_brier"], 0.0)


if __name__ == "__main__":
    unittest.main()
