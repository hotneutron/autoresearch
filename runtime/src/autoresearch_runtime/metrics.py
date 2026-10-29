"""Explicit typed conjunctive metrics; subject evaluators supply scientific meaning."""
from __future__ import annotations
import operator
from .contracts import finite, identifier
from .protocol import pointer

OPS = {"lt": operator.lt, "le": operator.le, "eq": operator.eq, "ge": operator.ge, "gt": operator.gt}


def validate_metrics(definitions):
    if not isinstance(definitions, list) or not definitions:
        raise ValueError("Declare metric and regression criteria")
    seen = set()
    for item in definitions:
        name = identifier(item["name"])
        if name in seen: raise ValueError("Duplicate metric identity")
        seen.add(name)
        if item.get("direction") not in ("lower", "higher") or item.get("op") not in OPS:
            raise ValueError("Declare metric direction and comparator")
        if not item.get("unit") or not item.get("meaning") or not item.get("pointer", "").startswith("/"):
            raise ValueError("Declare unit, semantics and JSON pointer")
        finite(item["threshold"])
        if finite(item.get("minimum_effect", 0)) < 0: raise ValueError("Effect margin cannot be negative")
    return definitions


def evaluate(definitions, result):
    validate_metrics(definitions)
    values, checks = {}, {}
    for item in definitions:
        value = finite(pointer(result, item["pointer"]))
        values[item["name"]] = value
        checks[item["name"]] = bool(OPS[item["op"]](value, item["threshold"]))
    return {"values": values, "checks": checks, "passed": all(checks.values())}
