"""Offline tests for BakaSU watcher: no GitHub API or device access required."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).with_name("watch_upstream.py")
spec = importlib.util.spec_from_file_location("watch_upstream", SCRIPT)
watch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watch)

A = "a" * 40
B = "b" * 40
IMAGE1 = "1" * 64
IMAGE2 = "2" * 64


def artifact(revision, image, when, *, expired=False, size=100):
    return {"name": f"bakasu-peridot-{revision}-{image}",
            "created_at": when, "expired": expired, "size_in_bytes": size}


class WatchTests(unittest.TestCase):
    def test_first_upstream_build(self):
        d = watch.choose(A, [])
        self.assertTrue(d["changed"])
        self.assertFalse(d["already_built"])
        self.assertEqual(d["previous_image_sha"], "")

    def test_already_built_skipped(self):
        d = watch.choose(A, [artifact(A, IMAGE1, "2026-10-14T00:00:00Z")])
        self.assertFalse(d["changed"])
        self.assertTrue(d["already_built"])

    def test_new_revision_retains_last_verified_image_guard(self):
        d = watch.choose(B, [artifact(A, IMAGE1, "2026-10-14T00:00:00Z")])
        self.assertTrue(d["changed"])
        self.assertEqual(d["previous_image_sha"], IMAGE1)

    def test_force_rebuild_existing_revision(self):
        d = watch.choose(A, [artifact(A, IMAGE1, "2026-10-14T00:00:00Z")], force=True)
        self.assertTrue(d["changed"])
        self.assertTrue(d["already_built"])

    def test_newer_history_takes_precedence(self):
        rows = [artifact(A, IMAGE1, "2026-10-10T00:00:00Z"),
                artifact(B, IMAGE2, "2026-10-13T00:00:00Z")]
        d = watch.choose("c"*40, rows)
        self.assertEqual(d["previous_image_sha"], IMAGE2)

    def test_expired_artifacts_do_not_block_build(self):
        d = watch.choose(A, [artifact(A, IMAGE1, "2026-10-14T00:00:00Z", expired=True)])
        self.assertTrue(d["changed"])

    def test_empty_artifact_does_not_block(self):
        d = watch.choose(A, [artifact(A, IMAGE1, "2026-10-14T00:00:00Z", size=0)])
        self.assertTrue(d["changed"])

    def test_malformed_artifact_does_not_affect_guard(self):
        d = watch.choose(B, [{"name": "bakasu-peridot-foo", "size_in_bytes": 50}])
        self.assertTrue(d["changed"])
        self.assertEqual(d["previous_image_sha"], "")

    def test_upstream_sha_strict(self):
        for value in ("B"*40, "xyz", "", "../BakaSU", "a"*39):
            with self.subTest(value=value), self.assertRaises(ValueError):
                watch.choose(value, [])

    def test_other_revisions_do_not_satisfy_current(self):
        d = watch.choose(B, [artifact(A, IMAGE1, "2026-10-14T00:00:00Z")])
        self.assertFalse(d["already_built"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
