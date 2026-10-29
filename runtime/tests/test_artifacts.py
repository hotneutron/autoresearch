import tempfile
import unittest
from pathlib import Path
from autoresearch_runtime.artifacts import ArtifactStore
from autoresearch_runtime.contracts import seal


class ArtifactTests(unittest.TestCase):
    def test_immutable_archive_and_offline_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); store = ArtifactStore(root / "archive")
            ref = store.put(b"measured evidence")
            manifest = seal({"id": "run-1", "artifacts": [ref]})
            store.commit(manifest)
            with self.assertRaises(ValueError):
                store.commit(seal({"id": "run-1", "artifacts": [ref], "changed": True}))
            bundle = store.export(manifest["sha256"])
            restored = ArtifactStore(root / "restored")
            restored.restore(bundle)
            self.assertEqual(restored.read(ref["sha256"]), b"measured evidence")
            (store.blobs / ref["sha256"]).write_bytes(b"changed")
            with self.assertRaises(ValueError): store.read(ref["sha256"])
            with self.assertRaises(ValueError): store.read("../escape")
