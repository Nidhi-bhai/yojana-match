#!/usr/bin/env python3
"""GET every apply and reference URL and report dead links.

Timeouts and TLS errors are unverified. Many government sites refuse a
non-Indian connection. A 404 or 410 is a failure. Run from the repo root:

    python3 scripts/check_links.py
    python3 scripts/check_links.py --local
"""

from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(__file__))
from link_fixes import DEAD_REFERENCE_URLS, is_dead_reference  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_PATH = os.path.join(ROOT, "data", "schemes.json")
UA = "Mozilla/5.0 (compatible; YojanaMatchLinkCheck/1.0)"
BLOCKED = (
    "164.100.",
    "translate.goog",
    "pmkvyofficial.org",
    "cscindia.info",
    "cgwcd.gov.in",
    "http://www.scholarships.gov.in",
    "RegistrationFormnew.aspx",
    "newstdRegfrmInstruction",
)


def collect(payload):
    found = []
    for scheme in payload["schemes"]:
        for kind in ("applyLinks", "references"):
            for link in scheme.get(kind) or []:
                url = link.get("url") or ""
                if url.startswith("http"):
                    found.append((scheme["slug"], kind, url))
    return found


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": UA}, method="GET")
    contexts = [None, ssl._create_unverified_context()]
    last_error = ""
    for context in contexts:
        try:
            with urllib.request.urlopen(request, timeout=12, context=context) as response:
                response.read(200)
                status = getattr(response, "status", 200)
                final = response.geturl()
                note = "ok" if context is None else "ok-unverified-cert"
                if status >= 400:
                    return "bad", status, final
                if "suspendedpage" in final or final.rstrip("/").endswith("/not-found"):
                    return "bad", status, final
                return note, status, final
        except urllib.error.HTTPError as error:
            if error.code in (404, 410):
                return "bad", error.code, url
            last_error = f"HTTP {error.code}"
            return "unverified", error.code, url
        except Exception as error:  # noqa: BLE001 - report the class and keep going
            last_error = f"{type(error).__name__}: {error}"
            continue
    return "unverified", last_error, url


def local_problems(rows, payload):
    problems = []
    blob = json.dumps(payload, ensure_ascii=False)
    for token in BLOCKED:
        if token in blob:
            problems.append(f"blocked pattern still in catalog: {token}")
    for url in DEAD_REFERENCE_URLS:
        if url in blob:
            problems.append(f"known 404 still in catalog: {url}")
    for slug, kind, url in rows:
        if is_dead_reference(url):
            problems.append(f"known 404 on {slug} {kind}: {url}")
        for token in BLOCKED:
            if token in url:
                problems.append(f"blocked pattern on {slug} {kind}: {url}")
    return problems


def main():
    with open(DATA_PATH, encoding="utf-8") as handle:
        payload = json.load(handle)
    rows = collect(payload)
    problems = local_problems(rows, payload)
    if problems:
        print(f"{len(problems)} catalog link problems")
        for item in problems:
            print(f"  {item}")
        raise SystemExit(1)
    if "--local" in sys.argv:
        print(f"Catalog clean: {len(rows)} apply and reference links, no known 404s or blocked domains.")
        return
    unique = sorted({url for _slug, _kind, url in rows})
    results = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fetch, url): url for url in unique}
        for future in as_completed(futures):
            url = futures[future]
            results[url] = future.result()
    bad = []
    unverified = []
    ok = 0
    for url in unique:
        state, detail, final = results[url]
        if state == "bad":
            bad.append((url, detail, final))
        elif state == "unverified":
            unverified.append((url, detail))
        else:
            ok += 1
    print(f"Checked {len(unique)} unique URLs: {ok} ok, {len(unverified)} unverified, {len(bad)} bad")
    if unverified:
        print("Unverified (timeout, TLS, or a non-404 HTTP error):")
        for url, detail in unverified:
            print(f"  {detail}  {url}")
    if bad:
        print("Bad:")
        for url, detail, final in bad:
            print(f"  {detail}  {url}  ->  {final}")
        raise SystemExit(1)
    print("No 404s and no blocked unofficial URLs in the catalog.")


if __name__ == "__main__":
    main()
