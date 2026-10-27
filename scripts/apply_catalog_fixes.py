#!/usr/bin/env python3
"""Refresh structured rules, official links, and the known Telugu mistranslation."""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from eligibility_rules import annotate_scheme  # noqa: E402
from link_fixes import fix_scheme_links  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_PATH = os.path.join(ROOT, "data", "schemes.json")
FINGERLING = ("వేలిముద్రలు", "ఫింగర్‌లింగ్‌లు (చేప పిల్లలు)")


def fix_telugu(value):
    if isinstance(value, str):
        return value.replace(FINGERLING[0], FINGERLING[1])
    if isinstance(value, list):
        return [fix_telugu(item) for item in value]
    if isinstance(value, dict):
        return {key: fix_telugu(item) for key, item in value.items()}
    return value


def main():
    with open(DATA_PATH, encoding="utf-8") as handle:
        payload = json.load(handle)
    schemes = []
    for scheme in payload["schemes"]:
        scheme = fix_telugu(scheme)
        scheme = fix_scheme_links(scheme)
        scheme = annotate_scheme(scheme)
        schemes.append(scheme)
    payload["schemes"] = schemes
    with open(DATA_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"Updated {len(schemes)} schemes")


if __name__ == "__main__":
    main()
