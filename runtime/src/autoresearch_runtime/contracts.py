"""Distributed protocol primitives. Execution request is preserved in M0 tracker."""
from __future__ import annotations
import hashlib
import json
import math
import re
from copy import deepcopy
from pathlib import PurePosixPath

DIST_PROTOCOL_VERSION = 1
DIST_STORE_VERSION = 1


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value):
        raise ValueError("Invalid distributed identifier")
    return value


def integer(value, *, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError("Expected a bounded nonnegative integer")
    return value


def finite(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("Expected a finite number")
    return value


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def hash_text(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("Expected full SHA-256")
    return value


def relative(value):
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("Expected a logical relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(v in ("..", ".") for v in value.split("/")) or "" in value.split("/"):
        raise ValueError("Path must remain inside its logical root")
    return value


def seal(value):
    body = deepcopy(value)
    body.pop("sha256", None)
    body.setdefault("schema_version", DIST_PROTOCOL_VERSION)
    body["sha256"] = digest(body)
    return body


def verify(value):
    if not isinstance(value, dict) or type(value.get("schema_version")) is not int or value.get("schema_version") != DIST_PROTOCOL_VERSION:
        raise ValueError("Unsupported distributed schema")
    body = deepcopy(value)
    expected = hash_text(body.pop("sha256", None))
    if digest(body) != expected:
        raise ValueError("Immutable contract hash changed")
    return body


def costs(value):
    if not isinstance(value, dict) or not value:
        raise ValueError("Declare finite cost dimensions")
    return {identifier(k): integer(v) for k, v in value.items()}


def add_costs(*values):
    result = {}
    for value in values:
        for key, amount in costs(value).items():
            result[key] = result.get(key, 0) + amount
    return result
