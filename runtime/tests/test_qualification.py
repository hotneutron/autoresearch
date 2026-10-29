import copy
import unittest
from autoresearch_runtime.contracts import digest, seal
from autoresearch_runtime.qualification import qualify, final_promotion


def evidence(value=2):
    candidate = {"id": "candidate", **{k: digest(k) for k in ("candidate_sha256", "benchmark_sha256", "evaluator_sha256", "environment_sha256")}}
    policy = {"replicates": [{"id": "r" + str(i), "seed": i} for i in range(3)], "direction": "lower", "minimum_effect": .1,
              "method": "paired_bootstrap", "confidence": .95, "comparisons": 4, "correction": "bonferroni", "analysis_seed": 17}
    samples = [{**candidate, "replicate_id": "r" + str(i), "seed": i, "value": value, "baseline": 4,
                "receipt_sha256": digest("receipt" + str(i)), "execution_status": "completed", "evidence_valid": True, "guards_passed": True} for i in range(3)]
    return candidate, samples, policy


class QualificationTests(unittest.TestCase):
    def test_positive_negative_and_exact_replicates(self):
        candidate, samples, policy = evidence()
        result = qualify(candidate, samples, policy)
        self.assertTrue(result["positive"])
        self.assertEqual(result["interval"], [2, 2])
        self.assertFalse(result["final_promotion"])
        candidate, samples, policy = evidence(5)
        self.assertFalse(qualify(candidate, samples, policy)["positive"])
        for mutation in ("seed", "execution_status", "environment_sha256", "guards_passed"):
            changed = copy.deepcopy(samples)
            changed[0][mutation] = {"seed": 99, "execution_status": "interrupted", "environment_sha256": digest("changed"), "guards_passed": False}[mutation]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): qualify(candidate, changed, policy)
        with self.assertRaises(ValueError): qualify(candidate, samples[:-1], policy)

    def test_final_binding_and_controls(self):
        candidate, samples, policy = evidence()
        with self.assertRaises(ValueError): qualify(candidate, samples, {**policy, "structured_search": True})
        with self.assertRaises(ValueError): qualify(candidate, samples, {**policy, "required_ablations": ["remove-change"]})
        q = qualify(candidate, samples, policy)
        confirmation = seal({"purpose": "fresh_confirmation", "protocol_valid": True, "aggregate": {"accepted": True}, "qualification_sha256": q["sha256"], "candidate_hashes": [candidate["candidate_sha256"]]})
        self.assertTrue(final_promotion(q, confirmation)["final_promotion"])
        with self.assertRaises(ValueError):
            final_promotion(q, seal({**confirmation, "aggregate": {"accepted": False}}))
        confirmation["qualification_sha256"] = digest("stale")
        with self.assertRaises(ValueError): final_promotion(q, seal(confirmation))
