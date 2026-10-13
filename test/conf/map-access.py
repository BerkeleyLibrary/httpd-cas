#!/usr/bin/env python3

"""
Returns
"""

import json
import os
import re
import sys

from collections import namedtuple, OrderedDict
from pathlib import Path


# mod_rewrite starts prg: maps with an empty environment, so httpd passes the
# root as an argument (expanded from ${MAPS_ROOT} in the config).
MAPS_ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("MAPS_ROOT", "/srv/geospatial")).resolve()
PUBLIC = b"Public\n"
RESTRICTED = b"Restricted\n"
VALID_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,254}$")
CACHE_MAX = 45_000


class RightsCache:
    def __init__(self, max_items=CACHE_MAX):
        self._cache = OrderedDict()
        self._max_items = max_items

    def set(self, map_id, rights, meta_stat):
        key = self._cachekey(meta_stat)
        self._cache[map_id] = (key, rights)
        self._cache.move_to_end(map_id)
        self._prune()

    def get(self, map_id, meta_stat):
        cached = self._cache.get(map_id)
        if cached and cached[0] == self._cachekey(meta_stat):
            self._cache.move_to_end(map_id)
            return cached[1]
        else:
            return None

    def rm(self, map_id):
        self._cache.pop(map_id, None)

    def _cachekey(self, meta_stat):
        return (
            meta_stat.st_dev,
            meta_stat.st_ino,
            meta_stat.st_size,
            meta_stat.st_mtime_ns,
            meta_stat.st_ctime_ns
        )

    def _prune(self):
        while len(self._cache) > self._max_items:
            self._cache.popitem(last=False)


def log(msg):
    try:
        sys.stderr.write(f"map-access: {msg}\n")
        sys.stderr.flush()
    except Exception:
        pass


def get_access_rights(map_id: str, rights_cache: RightsCache) -> bytes:
    log(f"Checking map: {map_id}")

    if not VALID_ID.match(map_id):
        return RESTRICTED

    geoblacklight_json = Path(MAPS_ROOT / map_id / "metadata" / "geoblacklight.json").resolve()
    log(f"Checking geoblacklight.json: {geoblacklight_json}")

    # Guard against symlinks pointing outside the maps tree.
    if not geoblacklight_json.is_relative_to(MAPS_ROOT):
        log(f"[restricted] path escapes root: {map_id} -> {geoblacklight_json}")
        return RESTRICTED

    # Ensure metadata exists
    try:
        st = geoblacklight_json.stat()
    except OSError as e:
        log(f"[restricted] error stat-ing {geoblacklight_json}: {e!r}")
        rights_cache.rm(map_id)
        return RESTRICTED

    if access_rights := rights_cache.get(map_id, st):
        return access_rights

    # Read accessRights from geoblacklight.json
    try:
        with geoblacklight_json.open('rb') as fh:
            doc = json.load(fh)

        access_rights = PUBLIC if is_public(doc) else RESTRICTED
        log(f"Determined access rights from file: {map_id} -> {access_rights}")
    except Exception as e:
        log(f"could not read {geoblacklight_json}: {e!r}")
        access_rights = RESTRICTED

    rights_cache.set(map_id, access_rights, st)

    return access_rights


def is_public(doc):
    value = doc.get('dct_accessRights_s', doc.get('dc_rights_s'))
    return isinstance(value, str) and value.strip() == "Public"


def main():
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    rights_cache = RightsCache()

    while True:
        line = stdin.readline()
        if not line:
            return

        try:
            map_id = line.decode('utf-8', 'strict').strip()
            access_rights = get_access_rights(map_id, rights_cache=rights_cache)
        except Exception as e:
            log(f"Unexpected error: {e!r}")
            access_rights = RESTRICTED

        try:
            stdout.write(access_rights)
            stdout.flush()
        except BrokenPipeError:
            return

if __name__ == "__main__":
    main()
