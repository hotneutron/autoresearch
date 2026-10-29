import tempfile
import unittest
from pathlib import Path
from autoresearch_runtime.global_store import GlobalStore, Conflict
from autoresearch_runtime.contracts import digest, seal
from autoresearch_runtime.portable_contract import bind_unit
import sys
from autoresearch_runtime.qualification import qualify
from autoresearch_runtime.search import Search
from autoresearch_runtime.review_policy import ReviewPolicy
from distributed_fixture import unit, round_plan


class SearchTests(unittest.TestCase):
    def test_twenty_four_candidate_fleet_bounds_and_global_frontier(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            store = GlobalStore(root / "global")
            store.register_project({"id": "subject", "goal_sha256": digest("finite-goal"), "budget": {"wall_ms": 200000}})
            for i in range(4):
                store.register_host({"id": "host-" + str(i), "boot_id": "boot", "capacity": 2, "profiles": ["local-direct"]})
            units = [unit(root, "candidate-" + str(i), value=i) for i in range(24)]
            plan = round_plan(units, concurrency=8)
            plan = seal({**plan, "top_k": 3})
            store.admit_round(plan)
            search = Search(store)
            evaluated = 0
            for wave in range(3):
                grants = []
                for index in range(8):
                    grants.append(store.claim({"id": "claim-" + str(wave) + "-" + str(index),
                        "host_id": "host-" + str(index // 2), "boot_id": "boot", "round_id": "round-1"}))
                self.assertEqual(sum(g["state"] == "claimed" for g in grants), 8)
                self.assertEqual(store.claim({"id": "extra-" + str(wave), "host_id": "host-0", "boot_id": "boot", "round_id": "round-1"})["state"], "no_capacity")
                for grant in grants:
                    output = root / grant["id"]
                    output.mkdir()
                    request = {"id": "start-" + grant["id"], "attempt_id": grant["id"],
                               **{k: grant[k] for k in ("host_id", "boot_id", "generation", "nonce")}}
                    request["binding"] = bind_unit(grant["unit"], {"framework": root / "framework", "subject": root / "subject", "output": output}, python=sys.executable)
                    store.authorize_start(request)
                    value = float(grant["unit"]["argv"][-1])
                    receipt = {"execution_status": "completed", "scientific_pass": True, "evidence_status": "valid", "costs": {"wall_ms": 10}}
                    store.commit_receipt({**request, "id": "receipt-" + grant["id"], "receipt": receipt})
                    candidate = {"id": grant["unit_id"], "candidate_sha256": grant["unit"]["sha256"],
                                 **{k: grant["unit"][k] for k in ("benchmark_sha256", "evaluator_sha256", "environment_sha256")}}
                    samples = [{**candidate, "replicate_id": "r", "seed": 0, "value": value, "baseline": 12,
                                "receipt_sha256": digest(receipt), "execution_status": "completed", "evidence_valid": True, "guards_passed": True}]
                    policy = {"replicates": [{"id": "r", "seed": 0}], "direction": "lower", "minimum_effect": .1,
                              "method": "deterministic_margin", "deterministic": True}
                    search.qualify_unit(grant["unit_id"], qualify(candidate, samples, policy))
                    evaluated += 1
            selection = search.seal_round("round-1")
            self.assertEqual(evaluated, 24)
            self.assertEqual(len(selection["inventory"]), 24)
            self.assertEqual([v["candidate_id"] for v in selection["selected"]], ["candidate-0", "candidate-1", "candidate-2"])
            self.assertEqual(store.accounting("subject")["charged"], {"wall_ms": 240})
            from autoresearch_runtime.context import build_context
            context = build_context(store, "round-1")
            self.assertEqual(len(context["units"]), 24)

    def test_complete_round_and_exact_review_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); store = GlobalStore(root / "global")
            store.register_project({"id": "subject", "goal_sha256": digest("finite-goal"), "budget": {"wall_ms": 100000}})
            store.register_host({"id": "host", "boot_id": "boot", "capacity": 2, "profiles": ["local-direct"]})
            units = [unit(root, "candidate-" + str(i)) for i in range(2)]
            plan = round_plan(units);store.admit_round(plan);search = Search(store)
            with self.assertRaises(Conflict): search.seal_round("round-1")
            for i in range(2):
                grant = store.claim({"id": "claim" + str(i), "host_id": "host", "boot_id": "boot", "round_id": "round-1"})
                request = {"id": "receipt" + str(i), "attempt_id": grant["id"], **{k:grant[k] for k in ("host_id", "boot_id", "generation", "nonce")}}
                output = root / ("out-" + str(i)); output.mkdir()
                start = {**request, "id": "start-" + str(i), "binding": bind_unit(grant["unit"], {"framework": root/"framework", "subject": root/"subject", "output": output}, python=sys.executable)}
                store.authorize_start(start)
                request["receipt"] = {"execution_status": "completed", "scientific_pass": True, "evidence_status": "valid", "costs": {"wall_ms": 1}}
                store.commit_receipt(request)
                candidate = {"id": grant["unit_id"], "candidate_sha256": grant["unit"]["sha256"], **{k:grant["unit"][k] for k in ("benchmark_sha256", "evaluator_sha256", "environment_sha256")}}
                samples = [{**candidate, "replicate_id": "r", "seed": 0, "value": i, "baseline": 4, "receipt_sha256": digest(request["receipt"]),
                            "execution_status": "completed", "evidence_valid": True, "guards_passed": True}]
                policy = {"replicates": [{"id": "r", "seed": 0}], "direction": "lower", "minimum_effect": .1, "method": "deterministic_margin", "deterministic": True}
                search.qualify_unit(grant["unit_id"], qualify(candidate, samples, policy))
            selection = search.seal_round("round-1")
            self.assertEqual(len(selection["selected"]), 2)
            next_plan = round_plan([unit(root, "next")], name="round-2", parent_round="round-1")
            with self.assertRaises(Conflict): store.admit_round(next_plan)
            reviewer = ReviewPolicy(store)
            review = seal({"id": "review", "project_id": "subject", "round_id": "round-1", "decision": "approve", "selection_sha256": selection["sha256"], "next_round_sha256": next_plan["sha256"]})
            self.assertFalse(reviewer.submit(review)["independence_verified"])
            self.assertEqual(reviewer.apply("review")["state"], "applied")
            store.admit_round(next_plan)
            self.assertEqual(store.snapshot("round-2")["rounds"][0]["state"], "active")

    def test_global_exposure_cannot_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);store=GlobalStore(root/"global")
            store.register_project({"id":"subject","goal_sha256":digest("finite-goal"),"budget":{"wall_ms":100000}})
            plan=round_plan([unit(root)]);store.admit_round(plan)
            opening=seal({"id":"opening","round_id":"round-1","project_id":"subject","population":"population", "subjects":["person-a"], "dataset_sha256":digest("labels"), "qualification_sha256":digest("q"), "candidate_hashes":[digest("candidate")], "purpose":"fresh_confirmation", "released_fields":{"accepted":"bool"}})
            store.reserve_confirmation(opening);store.begin_confirmation("opening")
            with self.assertRaises(Conflict):store.begin_confirmation("opening")
            with self.assertRaises(Conflict):store.reserve_confirmation(seal({**opening,"id":"renamed"}))
            result=store.finish_confirmation("opening",{"accepted":True},protocol_valid=True)
            self.assertTrue(result["protocol_valid"])
