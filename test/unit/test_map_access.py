"""Unit tests for test/conf/map-access.py (the RewriteMap prg: program)."""

import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parent.parent / "conf" / "map-access.py"

# The script's filename has a hyphen, so it can't be imported normally.
_spec = importlib.util.spec_from_file_location("map_access", SCRIPT)
map_access = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(map_access)

PUBLIC = map_access.PUBLIC
RESTRICTED = map_access.RESTRICTED


class MapsTestCase(unittest.TestCase):
    """Builds a throwaway maps root and points the module at it."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve() / "maps"
        self.root.mkdir()

        patcher = mock.patch.object(map_access, "MAPS_ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

        # Keep test output quiet; the script logs every lookup to stderr.
        stderr = redirect_stderr(io.StringIO())
        stderr.__enter__()
        self.addCleanup(stderr.__exit__, None, None, None)

        self.cache = map_access.RightsCache()

    def write_map(self, map_id, doc):
        meta = self.root / map_id / "metadata"
        meta.mkdir(parents=True, exist_ok=True)
        path = meta / "geoblacklight.json"
        path.write_text(doc if isinstance(doc, str) else json.dumps(doc))
        return path

    def rights(self, map_id):
        return map_access.get_access_rights(map_id, self.cache)


class RightsCacheTest(MapsTestCase):
    def setUp(self):
        super().setUp()
        self.path = self.write_map("m", {"dct_accessRights_s": "Public"})

    def test_miss_returns_none(self):
        self.assertIsNone(self.cache.get("m", self.path.stat()))

    def test_hit_returns_rights(self):
        self.cache.set("m", PUBLIC, self.path.stat())
        self.assertEqual(self.cache.get("m", self.path.stat()), PUBLIC)

    def test_rm(self):
        self.cache.set("m", PUBLIC, self.path.stat())
        self.cache.rm("m")
        self.cache.rm("never-cached")  # no error
        self.assertIsNone(self.cache.get("m", self.path.stat()))

    def test_stale_after_content_change(self):
        self.cache.set("m", PUBLIC, self.path.stat())
        self.path.write_text(json.dumps({"dct_accessRights_s": "Restricted"}))
        self.assertIsNone(self.cache.get("m", self.path.stat()))

    def test_stale_after_same_size_write_with_mtime_restored(self):
        # e.g. rsync --inplace -t: same size, same mtime, new content.
        before = self.path.stat()
        self.cache.set("m", PUBLIC, before)
        self.path.write_text(self.path.read_text().replace("Public", "Pxblic"))
        os.utime(self.path, ns=(before.st_atime_ns, before.st_mtime_ns))
        after = self.path.stat()
        self.assertEqual((after.st_size, after.st_mtime_ns), (before.st_size, before.st_mtime_ns))
        self.assertIsNone(self.cache.get("m", after))

    def test_stale_after_chmod(self):
        self.cache.set("m", RESTRICTED, self.path.stat())
        self.path.chmod(0o600)
        self.assertIsNone(self.cache.get("m", self.path.stat()))

    def test_stale_after_atomic_replace(self):
        self.cache.set("m", PUBLIC, self.path.stat())
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(self.path.read_text())
        tmp.replace(self.path)
        self.assertIsNone(self.cache.get("m", self.path.stat()))

    def test_evicts_least_recently_used(self):
        cache = map_access.RightsCache(max_items=2)
        st = self.path.stat()
        cache.set("a", PUBLIC, st)
        cache.set("b", PUBLIC, st)
        cache.get("a", st)            # a is now most recently used
        cache.set("c", PUBLIC, st)    # evicts b
        self.assertEqual(cache.get("a", st), PUBLIC)
        self.assertIsNone(cache.get("b", st))
        self.assertEqual(cache.get("c", st), PUBLIC)

    def test_set_existing_key_refreshes_recency(self):
        cache = map_access.RightsCache(max_items=2)
        st = self.path.stat()
        cache.set("a", PUBLIC, st)
        cache.set("b", PUBLIC, st)
        cache.set("a", RESTRICTED, st)  # update a, making b the oldest
        cache.set("c", PUBLIC, st)
        self.assertEqual(cache.get("a", st), RESTRICTED)
        self.assertIsNone(cache.get("b", st))

    def test_never_exceeds_max_items(self):
        cache = map_access.RightsCache(max_items=3)
        st = self.path.stat()
        for i in range(10):
            cache.set(f"m{i}", PUBLIC, st)
        self.assertEqual(len(cache._cache), 3)


class AccessRightsTest(MapsTestCase):
    def test_dct_access_rights_public(self):
        self.write_map("m", {"dct_accessRights_s": "Public"})
        self.assertEqual(self.rights("m"), PUBLIC)

    def test_dct_access_rights_restricted(self):
        self.write_map("m", {"dct_accessRights_s": "Restricted"})
        self.assertEqual(self.rights("m"), RESTRICTED)

    def test_dc_rights_fallback(self):
        self.write_map("m", {"dc_rights_s": "Public"})
        self.assertEqual(self.rights("m"), PUBLIC)

    def test_dct_access_rights_takes_precedence(self):
        self.write_map("m", {"dct_accessRights_s": "Restricted", "dc_rights_s": "Public"})
        self.assertEqual(self.rights("m"), RESTRICTED)

    def test_surrounding_whitespace_is_ignored(self):
        self.write_map("m", {"dct_accessRights_s": " Public\n"})
        self.assertEqual(self.rights("m"), PUBLIC)

    def test_restricted_values(self):
        for doc in [
            {},
            {"dct_accessRights_s": None},
            {"dct_accessRights_s": "public"},
            {"dct_accessRights_s": ["Public"]},
            {"dct_accessRights_s": True},
            [],
            "not json",
            "",
        ]:
            with self.subTest(doc=doc):
                self.cache = map_access.RightsCache()
                self.write_map("m", doc)
                self.assertEqual(self.rights("m"), RESTRICTED)

    def test_invalid_ids(self):
        self.write_map("m", {"dct_accessRights_s": "Public"})
        for map_id in ["", ".", "..", ".m", "-m", "m/x", "../maps/m", "m\x00", "m m", "a" * 256]:
            with self.subTest(map_id=map_id):
                self.assertEqual(self.rights(map_id), RESTRICTED)

    def test_longest_valid_id(self):
        self.write_map("a" * 255, {"dct_accessRights_s": "Public"})
        self.assertEqual(self.rights("a" * 255), PUBLIC)

    def test_missing_metadata(self):
        (self.root / "m").mkdir()
        self.assertEqual(self.rights("m"), RESTRICTED)
        self.assertEqual(self.rights("nonexistent"), RESTRICTED)

    def test_symlink_escaping_root(self):
        outside = self.root.parent / "outside"
        outside.mkdir()
        (outside / "metadata").mkdir()
        (outside / "metadata" / "geoblacklight.json").write_text('{"dct_accessRights_s": "Public"}')
        (self.root / "m").symlink_to(outside)
        self.assertEqual(self.rights("m"), RESTRICTED)

    def test_symlink_within_root(self):
        self.write_map("real", {"dct_accessRights_s": "Public"})
        (self.root / "alias").symlink_to(self.root / "real")
        self.assertEqual(self.rights("alias"), PUBLIC)


class CachingTest(MapsTestCase):
    def test_second_lookup_is_served_from_cache(self):
        self.write_map("m", {"dct_accessRights_s": "Public"})
        self.assertEqual(self.rights("m"), PUBLIC)
        with mock.patch.object(map_access.json, "load", side_effect=AssertionError("re-read")):
            self.assertEqual(self.rights("m"), PUBLIC)

    def test_metadata_change_is_picked_up(self):
        path = self.write_map("m", {"dct_accessRights_s": "Public"})
        self.assertEqual(self.rights("m"), PUBLIC)
        path.write_text(json.dumps({"dct_accessRights_s": "Restricted"}))
        self.assertEqual(self.rights("m"), RESTRICTED)

    def test_deleted_metadata_is_restricted_and_evicted(self):
        path = self.write_map("m", {"dct_accessRights_s": "Public"})
        self.assertEqual(self.rights("m"), PUBLIC)
        path.unlink()
        self.assertEqual(self.rights("m"), RESTRICTED)
        self.assertNotIn("m", self.cache._cache)

    def test_parse_error_recovers_once_file_is_fixed(self):
        path = self.write_map("m", '{"dct_accessRights_s": "Pub')
        self.assertEqual(self.rights("m"), RESTRICTED)
        path.write_text(json.dumps({"dct_accessRights_s": "Public"}))
        self.assertEqual(self.rights("m"), PUBLIC)

    @unittest.skipIf(os.geteuid() == 0, "root ignores file permissions")
    def test_permission_error_recovers_after_chmod(self):
        path = self.write_map("m", {"dct_accessRights_s": "Public"})
        path.chmod(0o000)
        self.addCleanup(path.chmod, 0o644)
        self.assertEqual(self.rights("m"), RESTRICTED)
        path.chmod(0o644)
        self.assertEqual(self.rights("m"), PUBLIC)

    @unittest.skipIf(os.geteuid() == 0, "root ignores file permissions")
    def test_unreadable_metadata_dir_is_restricted_and_evicted(self):
        path = self.write_map("m", {"dct_accessRights_s": "Public"})
        self.assertEqual(self.rights("m"), PUBLIC)
        path.parent.chmod(0o000)
        self.addCleanup(path.parent.chmod, 0o755)
        self.assertEqual(self.rights("m"), RESTRICTED)
        self.assertNotIn("m", self.cache._cache)


class ProtocolTest(unittest.TestCase):
    """Runs the script the way mod_rewrite does: root as argv[1], empty env."""

    def test_one_answer_per_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "maps"
            for map_id, rights in [("pub", "Public"), ("res", "Restricted")]:
                (root / map_id / "metadata").mkdir(parents=True)
                (root / map_id / "metadata" / "geoblacklight.json").write_text(
                    json.dumps({"dct_accessRights_s": rights}))

            requests = [b"pub", b"res", b"missing", b"../etc", b"\xff\xfe", b"", b"pub"]
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), str(root)],
                input=b"".join(r + b"\n" for r in requests),
                capture_output=True,
                env={},
                timeout=10,
            )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.splitlines(), [
            b"Public", b"Restricted", b"Restricted", b"Restricted",
            b"Restricted", b"Restricted", b"Public",
        ])
        # The cache must persist across lines: "pub" is read from disk only once.
        self.assertEqual(proc.stderr.count(b"Determined access rights from file: pub"), 1, proc.stderr)


if __name__ == "__main__":
    unittest.main()
