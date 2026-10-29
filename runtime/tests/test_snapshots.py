import tempfile
import unittest
import subprocess
from pathlib import Path
from autoresearch_runtime.artifacts import ArtifactStore
from autoresearch_runtime.snapshots import Snapshots
from autoresearch_runtime.workspace_pool import WorkspacePool
from autoresearch_runtime.promotion import promote
from distributed_fixture import git_repo


class SnapshotTests(unittest.TestCase):
    def test_archive_restore_and_bounded_promotion(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);repository=root/'subject';ref=git_repo(repository,{'code.py':'print(1)'})
            snapshots=Snapshots(ArtifactStore(root/'archive'));manifest=snapshots.capture(repository,ref['commit'],'candidate')
            restored=snapshots.restore(manifest,root/'restored')
            self.assertEqual((restored/'code.py').read_text(),'print(1)')
            promote(repository,{'path-a':ref['commit']},{},top_k=1)
            with self.assertRaises(subprocess.CalledProcessError):promote(repository,{'path-a':ref['commit']},{'path-a':'0'*40},top_k=1)
            with self.assertRaises(ValueError):promote(repository,{'a':ref['commit'],'b':ref['commit']},{},top_k=1)
    def test_pool_capacity_is_live_lease_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            pool=WorkspacePool(directory,1);slot=pool.acquire()
            try:
                with self.assertRaises(BlockingIOError):pool.acquire()
            finally:slot['lease'].close()
            replacement=pool.acquire();self.assertEqual(replacement['slot'],0);replacement['lease'].close()
