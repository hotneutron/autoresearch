import copy
import tempfile
import unittest
from pathlib import Path
from autoresearch_runtime.contracts import digest, relative, seal, verify
from autoresearch_runtime.experiment_spec import compile_spec
from autoresearch_runtime.metrics import evaluate
from autoresearch_runtime.portable_contract import bind_unit
from autoresearch_runtime.costs import reservation, within
from distributed_fixture import unit
import sys


class ContractTests(unittest.TestCase):
    def test_sealing_and_typed_boundaries(self):
        value = seal({"id": "fixed", "nested": [1, 2]})
        self.assertEqual(verify(value)["id"], "fixed")
        value["nested"].append(3)
        with self.assertRaises(ValueError): verify(value)
        for path in ("../escape", "/absolute", "a//b", "a/./b", "a\\b"):
            with self.subTest(path=path), self.assertRaises(ValueError): relative(path)
        self.assertEqual(reservation(prepare_ms=10, execution_ms=20, evaluation_ms=30, grace_ms=40, gpu_count=2, rate_microcurrency_per_second=15), {"wall_ms": 100, "gpu_ms": 200, "microcurrency": 2})
        self.assertFalse(within({"wall_ms": 101}, {"wall_ms": 100}))

    def test_frozen_spec_and_host_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); spec = unit(root)
            output = root / "out"; output.mkdir()
            roots = {"framework": root / "framework", "subject": root / "subject", "output": output}
            binding = bind_unit(spec, roots, python=sys.executable)
            self.assertEqual(binding["unit_sha256"], spec["sha256"])
            self.assertEqual(binding["argv"][2], str(output / "result.json"))
            (root / "subject/metric.py").write_text("changed")
            with self.assertRaises(ValueError): bind_unit(spec, roots, python=sys.executable)
            for change in ({"partition": "final"}, {"timeout_ms": -1}, {"costs": {"wall_ms": True}}):
                altered = {**spec, **change}
                with self.subTest(change=change), self.assertRaises(ValueError): compile_spec(altered)

    def test_joint_metrics_and_finite_values(self):
        with tempfile.TemporaryDirectory() as directory:
            definitions = unit(Path(directory))["metrics"]
            self.assertTrue(evaluate(definitions, {"score": 0})["passed"])
            self.assertFalse(evaluate(definitions, {"score": 11})["passed"])
            for value in (True, float("nan"), float("inf")):
                with self.subTest(value=value), self.assertRaises(ValueError): evaluate(definitions, {"score": value})
