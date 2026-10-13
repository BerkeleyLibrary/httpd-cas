#!/usr/bin/env python3

"""
Returns
"""

import functools
import json
import os
import re
import sys

from collections import namedtuple, OrderedDict
from pathlib import Path


# mod_rewrite starts prg: maps with an empty environment, so httpd passes the
# root as an argument (expanded from ${MAPS_ROOT} in the config).
MAPS_ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("MAPS_ROOT", "/srv/geospatial")).resolve()
RIGHTS_FIELD_NAME = "dc_rights_s"
PUBLIC = b"Public\n"
RESTRICTED = b"Restricted\n"
VALID_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,254}$")
CACHE_MAX = 45_000


CacheKey = namedtuple('CacheKey', ['mtime_ns', 'size', 'inode'])
_cache = OrderedDict() # map_id -> (CacheKey, access_rights)


def log(msg):
    try:
        sys.stderr.write(f"map-access: {msg}\n")
        sys.stderr.flush()
    except Exception:
        pass


def get_access_rights(map_id):
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
    except FileNotFoundError:
        log(f"[restricted] geoblacklight.json is missing: {map_id} -> {geoblacklight_json}")
        _cache.pop(map_id, None)
        return RESTRICTED

    # Check the cache. File modifications invalidate the cache entry.
    key = CacheKey(mtime_ns=st.st_mtime_ns, size=st.st_size, inode=st.st_ino)
    cached = _cache.get(map_id)
    if cached and cached[0] == key:
        _cache.move_to_end(map_id)
        access_rights = cached[1]
        log(f"[cached] fetched access right from cache: {map_id} -> {access_rights}")
        return access_rights

    # Read accessRights from geoblacklight.json
    try:
        with geoblacklight_json.open('rb') as fh:
            doc = json.load(fh)

        access_rights = PUBLIC if is_public(doc.get(RIGHTS_FIELD_NAME)) else RESTRICTED
        log(f"Determined access rights from file: {map_id} -> {access_rights}")
    except Exception as e:
        log(f"could not read {geoblacklight_json}: {e!r}")
        access_rights = RESTRICTED

    # Eject cache entries til you're under the cap
    _cache[map_id] = (key, access_rights)
    _cache.move_to_end(map_id)
    while len(_cache) > CACHE_MAX:
        _cache.popitem(last=False)

    return access_rights


def is_public(value):
    """dct_accessRights_s is normally a string, but tolerate a 1-item list."""
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    return isinstance(value, str) and value.strip() == "Public"


def main():
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer

    while True:
        line = stdin.readline()
        if not line:
            return

        try:
            map_id = line.decode('utf-8', 'strict').strip()
            access_rights = get_access_rights(map_id)
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
