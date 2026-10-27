#!/usr/bin/env python3
"""Build data/schemes.json from the public myScheme API.

Reads the API key from MY_SCHEME_API_KEY or MSKEY. The key is not written to disk.
Scheme text, links, and facet tags are copied from the API. Unknown amounts stay blank.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(__file__))
from scheme_text import (  # noqa: E402
    age_bounds,
    benefit_amount,
    clean_text,
    document_lines,
    enrich_criteria,
    income_ceiling,
    male_must_be_sc_st,
    slate_to_text,
)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT_PATH = os.path.join(ROOT, "data", "schemes.json")
CACHE = "/tmp/yojana-cache"
API = "https://api.myscheme.gov.in"
LAST_VERIFIED = "2026-10-27"
TEST_AGES = [0, 6, 10, 14, 17, 18, 21, 25, 30, 35, 40, 45, 50, 55, 59, 60, 65, 70, 80, 100]

TARGET_STATES = {
    "Andhra Pradesh": 12,
    "Telangana": 12,
    "Uttar Pradesh": 12,
    "Maharashtra": 12,
    "Karnataka": 12,
    "Tamil Nadu": 12,
    "Bihar": 12,
    "Rajasthan": 8,
    "West Bengal": 8,
    "Madhya Pradesh": 8,
    "Gujarat": 8,
    "Kerala": 8,
    "Odisha": 8,
    "Delhi": 6,
    "Punjab": 6,
    "Haryana": 6,
    "Assam": 6,
    "Jharkhand": 6,
    "Chhattisgarh": 6,
}

BOOSTS = [
    ("pradhan mantri", 8),
    ("pm-kisan", 12),
    ("kisan samman", 12),
    ("pension", 6),
    ("scholarship", 6),
    ("awas", 6),
    ("ujjwala", 8),
    ("ayushman", 8),
    ("bima", 5),
    ("mudra", 6),
    ("matru", 6),
    ("fasal", 6),
    ("svanidhi", 8),
    ("vishwakarma", 6),
    ("jan dhan", 6),
    ("disability", 4),
    ("widow", 5),
    ("girl", 3),
    ("women", 3),
    ("farmer", 4),
    ("rythu", 8),
    ("ysr", 6),
    ("jagananna", 6),
    ("gruha", 7),
    ("ladli", 6),
    ("ladki", 6),
    ("kanya", 5),
    ("bahin", 6),
    ("magalir", 7),
    ("aasara", 6),
    ("vidya", 4),
    ("amma", 4),
    ("cheyutha", 7),
    ("shaadi", 5),
    ("kalyana", 5),
    ("subsidy", 3),
    ("insurance", 3),
    ("stipend", 3),
    ("mukhyamantri", 5),
    ("mukhya mantri", 5),
    ("chief minister", 4),
]
DOWNS = (
    "internship",
    "fellowship",
    "puraskar",
    " medal",
    "award",
    "research grant",
    "export promotion",
)
FORCE_SLUGS = {
    "pm-kisan",
    "pmfby",
    "pmkmdy",
    "kcc",
    "pmgsy",
    "sui",
    "pmsby",
    "pmuy",
    "pmuy2",
    "pmmvy",
    "pm-poshan",
    "pmsma",
    "post-st",
    "pmjjby",
    "apy",
    "pmjdy",
    "pmegp",
    "pm-svanidhi",
    "pm-vishwakarma",
    "jsy",
}
FORCE_PHRASES = (
    "pradhan mantri kisan samman",
    "ayushman bharat",
    "pradhan mantri awas",
    "ujjwala",
    "matru vandana",
    "jeevan jyoti",
    "suraksha bima",
    "atal pension",
    "fasal bima",
    "stand-up india",
    "standup india",
    "jan dhan",
    "vishwakarma",
    "svanidhi",
    "indira gandhi national old age",
    "mahatma gandhi national rural employment",
)


class Client:
    def __init__(self, key: str):
        self.key = key

    def get_json(self, url: str):
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "YojanaMatchDataBot/1.0 (public scheme catalog; +https://github.com/Nidhi-bhai/yojana-match)",
                "Origin": "https://www.myscheme.gov.in",
                "Referer": "https://www.myscheme.gov.in/",
                "x-api-key": self.key,
                "Accept": "application/json",
            },
        )
        last_error = None
        for attempt in range(5):
            try:
                with urllib.request.urlopen(request, timeout=50) as response:
                    return json.load(response)
            except urllib.error.HTTPError as error:
                last_error = error
                if error.code in (429, 500, 502, 503, 504):
                    time.sleep(1.2 * (attempt + 1))
                    continue
                body = error.read()[:200]
                raise RuntimeError(f"HTTP {error.code} {url} {body!r}") from error
            except Exception as error:  # noqa: BLE001
                last_error = error
                time.sleep(0.8 * (attempt + 1))
        raise RuntimeError(f"Failed {url}: {last_error}")


def search_page(client: Client, filters, start, size, sort="schemename-asc"):
    query = urllib.parse.quote(json.dumps(filters, separators=(",", ":")))
    url = (
        f"{API}/search/v6/schemes?lang=en&q={query}&keyword=&sort={urllib.parse.quote(sort)}"
        f"&from={start}&size={size}"
    )
    payload = client.get_json(url)
    hits = payload["data"]["hits"]
    return hits["page"], hits["items"]


def collect_records(client: Client, filters, sort="schemename-asc"):
    start = 0
    size = 100
    records = []
    total = None
    while True:
        page, items = search_page(client, filters, start, size, sort)
        if total is None:
            total = page["total"]
        if not items:
            break
        for item in items:
            fields = item.get("fields") or {}
            slug = fields.get("slug")
            name = fields.get("schemeName")
            if not slug or not name:
                continue
            records.append(
                {
                    "slug": slug,
                    "name": name.strip(),
                    "level": fields.get("level") or "",
                    "states": list(fields.get("beneficiaryState") or []),
                    "categories": list(fields.get("schemeCategory") or []),
                    "ministry": fields.get("nodalMinistryName") or "",
                    "shortTitle": fields.get("schemeShortTitle") or "",
                }
            )
        start += len(items)
        if start >= total:
            break
    if total is not None and len(records) != total:
        print(f"  warn expected {total} records, kept {len(records)} for {filters}", flush=True)
    return records


def collect_slugs(client: Client, filters):
    start = 0
    size = 100
    slugs = set()
    total = None
    while True:
        page, items = search_page(client, filters, start, size, "")
        if total is None:
            total = page["total"]
        if not items:
            break
        for item in items:
            slug = (item.get("fields") or {}).get("slug")
            if slug:
                slugs.add(slug)
        start += len(items)
        if start >= total:
            break
    return slugs, total or 0


def score_name(name: str) -> int:
    lowered = name.lower()
    value = 0
    for phrase, weight in BOOSTS:
        if phrase in lowered:
            value += weight
    for phrase in DOWNS:
        if phrase in lowered:
            value -= 8
    return value


def is_forced(record) -> bool:
    if record["slug"] in FORCE_SLUGS:
        return True
    lowered = record["name"].lower()
    return any(phrase in lowered for phrase in FORCE_PHRASES)


def select_records(central, by_state):
    picked = []
    seen = set()

    def add(record):
        if record["slug"] in seen:
            return
        seen.add(record["slug"])
        picked.append(record)

    forced = [record for record in central if is_forced(record)]
    ranked = sorted(central, key=lambda record: (-score_name(record["name"]), record["name"]))
    for record in forced:
        add(record)
    central_count = len(picked)
    for record in ranked:
        if central_count >= 80:
            break
        before = len(picked)
        add(record)
        central_count += len(picked) - before
    for state, limit in TARGET_STATES.items():
        pool = sorted(by_state.get(state, []), key=lambda record: (-score_name(record["name"]), record["name"]))
        added = 0
        for record in pool:
            if added >= limit:
                break
            before = len(picked)
            add(record)
            added += len(picked) - before
    if len(picked) > 240:
        forced_slugs = {record["slug"] for record in forced}
        trimmed = []
        state_overflow = [
            record
            for record in picked
            if record["slug"] not in forced_slugs and record["level"] != "Central"
        ]
        state_overflow.sort(key=lambda record: (score_name(record["name"]), record["name"]))
        drop = set()
        extra = len(picked) - 240
        for record in state_overflow:
            if extra <= 0:
                break
            drop.add(record["slug"])
            extra -= 1
        for record in picked:
            if record["slug"] not in drop:
                trimmed.append(record)
        picked = trimmed
    return picked


def cache_path(name: str) -> str:
    safe = name.replace("/", "_")
    return os.path.join(CACHE, safe)


def cached_get(client: Client, name: str, url: str):
    path = cache_path(name)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    payload = client.get_json(url)
    os.makedirs(CACHE, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)
    return payload


def lang_block(payload, lang):
    if not isinstance(payload, dict) or payload.get("statusCode") not in (200, "200"):
        return None
    data = payload.get("data") or {}
    block = data.get(lang)
    if isinstance(block, dict):
        return data.get("_id"), block
    return data.get("_id"), None


def localized_copy(block):
    if not block:
        return {"brief": "", "benefits": "", "eligibility": "", "howToApply": "", "name": ""}
    basic = block.get("basicDetails") or {}
    content = block.get("schemeContent") or {}
    eligibility = (block.get("eligibilityCriteria") or {}).get("eligibilityDescription_md") or ""
    if not eligibility:
        eligibility = slate_to_text((block.get("eligibilityCriteria") or {}).get("eligibilityDescription"))
    steps = []
    for process in block.get("applicationProcess") or []:
        text = clean_text(process.get("process_md") or "")
        if not text:
            text = slate_to_text(process.get("process"))
        if text:
            steps.append(text)
    return {
        "name": clean_text(basic.get("schemeName") or ""),
        "brief": clean_text(content.get("briefDescription") or ""),
        "benefits": clean_text(content.get("benefits_md") or "") or slate_to_text(content.get("benefits")),
        "eligibility": clean_text(eligibility),
        "howToApply": "\n\n".join(steps).strip(),
    }


def apply_links(block):
    links = []
    seen = set()
    for process in (block or {}).get("applicationProcess") or []:
        url = process.get("url")
        if not isinstance(url, str):
            continue
        url = url.strip()
        if not url.startswith("http") or url in seen:
            continue
        seen.add(url)
        links.append({"mode": process.get("mode") or "", "url": url})
    return links


def references_from(block):
    refs = []
    seen = set()
    for item in ((block or {}).get("schemeContent") or {}).get("references") or []:
        url = (item or {}).get("url")
        title = clean_text((item or {}).get("title") or "")
        if not isinstance(url, str):
            continue
        url = url.strip()
        if not url.startswith("http") or url in seen:
            continue
        seen.add(url)
        refs.append({"title": title, "url": url})
    return refs


def ministry_of(block, fallback):
    basic = (block or {}).get("basicDetails") or {}
    node = basic.get("nodalMinistryName")
    if isinstance(node, dict) and node.get("label"):
        return node["label"]
    if isinstance(node, str) and node:
        return node
    return fallback or ""


def build_scheme(client: Client, meta, facets):
    slug = meta["slug"]
    english_payload = cached_get(
        client,
        f"{slug}-en.json",
        f"{API}/schemes/v6/public/schemes?slug={urllib.parse.quote(slug)}&lang=en",
    )
    scheme_id, english = lang_block(english_payload, "en")
    if not english:
        raise RuntimeError(f"no english block for {slug}")
    hindi_payload = cached_get(
        client,
        f"{slug}-hi.json",
        f"{API}/schemes/v6/public/schemes?slug={urllib.parse.quote(slug)}&lang=hi",
    )
    telugu_payload = cached_get(
        client,
        f"{slug}-te.json",
        f"{API}/schemes/v6/public/schemes?slug={urllib.parse.quote(slug)}&lang=te",
    )
    _, hindi = lang_block(hindi_payload, "hi")
    _, telugu = lang_block(telugu_payload, "te")
    copies = {
        "en": localized_copy(english),
        "hi": localized_copy(hindi),
        "te": localized_copy(telugu),
    }
    documents = {"en": [], "hi": [], "te": []}
    if scheme_id:
        for lang in ("en", "hi", "te"):
            try:
                payload = cached_get(
                    client,
                    f"{slug}-docs-{lang}.json",
                    f"{API}/schemes/v6/public/schemes/{scheme_id}/documents?lang={lang}",
                )
            except Exception:
                continue
            data = (payload or {}).get("data") or {}
            block = data.get(lang) if isinstance(data, dict) else None
            if not isinstance(block, dict) and lang != "en":
                block = data.get("en") if isinstance(data, dict) else None
            documents[lang] = document_lines(block if isinstance(block, dict) else {})
    basic = english.get("basicDetails") or {}
    eligibility = copies["en"]["eligibility"]
    benefits = copies["en"]["benefits"]
    ceiling, ceiling_note = income_ceiling(eligibility)
    quote = male_must_be_sc_st(eligibility)
    covered = sorted(facets["ages"].get(slug, []))
    age_min, age_max = age_bounds(covered, TEST_AGES)
    genders = sorted(facets["gender"].get(slug, []))
    castes = sorted(facets["caste"].get(slug, []))
    residences = sorted(facets["residence"].get(slug, []))
    occupations = sorted(facets["occupation"].get(slug, []))
    employment = sorted(facets["employment"].get(slug, []))
    disability = None
    if slug in facets["disability_yes"]:
        disability = "Yes"
    elif slug in facets["disability_no"]:
        disability = "No"
    student_only = None
    if slug in facets["student_yes"]:
        student_only = True
    elif slug in facets["student_no"]:
        student_only = False
    bpl_only = None
    if slug in facets["bpl_yes"]:
        bpl_only = True
    elif slug in facets["bpl_no"]:
        bpl_only = False
    close_date = basic.get("schemeCloseDate") or None
    if close_date in ("", "null"):
        close_date = None
    scheme = {
        "slug": slug,
        "shortTitle": meta.get("shortTitle") or basic.get("schemeShortTitle") or "",
        "name": {
            "en": copies["en"]["name"] or meta["name"],
            "hi": copies["hi"]["name"],
            "te": copies["te"]["name"],
        },
        "level": basic.get("level", {}).get("label") if isinstance(basic.get("level"), dict) else meta.get("level"),
        "states": meta.get("states") or [],
        "categories": [
            item.get("label")
            for item in (basic.get("schemeCategory") or [])
            if isinstance(item, dict) and item.get("label")
        ] or meta.get("categories") or [],
        "ministry": ministry_of(english, meta.get("ministry")),
        "schemeFor": basic.get("schemeFor") or "",
        "openDate": basic.get("schemeOpenDate") or "",
        "closeDate": close_date,
        "brief": {lang: copies[lang]["brief"] for lang in ("en", "hi", "te")},
        "benefits": {lang: copies[lang]["benefits"] for lang in ("en", "hi", "te")},
        "benefitAmount": benefit_amount(benefits),
        "eligibility": {lang: copies[lang]["eligibility"] for lang in ("en", "hi", "te")},
        "howToApply": {lang: copies[lang]["howToApply"] for lang in ("en", "hi", "te")},
        "documents": documents,
        "applyLinks": apply_links(english),
        "references": references_from(english),
        "sourceUrl": f"https://www.myscheme.gov.in/schemes/{slug}",
        "lastVerified": LAST_VERIFIED,
        "criteria": enrich_criteria({
            "genders": genders,
            "castes": castes,
            "residences": residences,
            "occupations": occupations,
            "employment": employment,
            "disability": disability,
            "studentOnly": student_only,
            "bplOnly": bpl_only,
            "ageMin": age_min,
            "ageMax": age_max,
            "ageSamples": covered,
            "incomeCeilingInr": ceiling,
            "incomeCeilingNote": ceiling_note,
            "genderCasteMode": "male-must-be-sc-st" if quote else "",
            "genderCasteQuote": quote,
        }, eligibility),
    }
    return scheme


def facet_value_map(client: Client, identifier, values, selected):
    mapping = {slug: set() for slug in selected}
    for value in values:
        slugs, total = collect_slugs(client, [{"identifier": identifier, "value": value}])
        print(f"  facet {identifier}={value}: {len(slugs)}/{total}", flush=True)
        if total and len(slugs) < total * 0.98:
            raise RuntimeError(f"Incomplete facet scan {identifier}={value}")
        for slug in selected:
            if slug in slugs:
                mapping[slug].add(value)
    return mapping


def main():
    key = os.environ.get("MY_SCHEME_API_KEY") or os.environ.get("MSKEY")
    if not key or len(key) < 20:
        print("Set MY_SCHEME_API_KEY to the public myScheme read key.", file=sys.stderr)
        return 1
    client = Client(key)
    os.makedirs(CACHE, exist_ok=True)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

    print("Listing central schemes", flush=True)
    central = collect_records(client, [{"identifier": "level", "value": "Central"}])
    print(f"  central {len(central)}", flush=True)
    by_state = {}
    for state in TARGET_STATES:
        print(f"Listing {state}", flush=True)
        by_state[state] = collect_records(
            client,
            [
                {"identifier": "beneficiaryState", "value": state},
                {"identifier": "level", "value": "State"},
            ],
        )
        print(f"  {state} {len(by_state[state])}", flush=True)

    sample = client.get_json(f"{API}/search/v6/schemes?lang=en&q=%5B%5D&keyword=&sort=&from=0&size=1")
    facets = sample["data"]["facets"]
    states = []
    categories = []
    for facet in facets:
        if facet["identifier"] == "beneficiaryState":
            states = [entry["label"] for entry in facet["entries"] if entry["label"] != "All"]
        if facet["identifier"] == "schemeCategory":
            categories = [entry["label"] for entry in facet["entries"]]

    selected = select_records(central, by_state)
    selected_slugs = [record["slug"] for record in selected]
    print(f"Selected {len(selected_slugs)} schemes", flush=True)

    def labels_for(identifier):
        for facet in facets:
            if facet.get("identifier") == identifier:
                return [entry["label"] for entry in facet.get("entries") or [] if entry.get("label")]
        raise RuntimeError(f"Missing facet {identifier}")

    print("Scanning facets", flush=True)
    gender = facet_value_map(client, "gender", labels_for("gender"), selected_slugs)
    caste = facet_value_map(client, "caste", labels_for("caste"), selected_slugs)
    residence = facet_value_map(client, "residence", labels_for("residence"), selected_slugs)
    occupation = facet_value_map(client, "occupation", labels_for("occupation"), selected_slugs)
    employment = facet_value_map(
        client, "employmentStatus", labels_for("employmentStatus"), selected_slugs
    )
    disability_yes, disability_yes_total = collect_slugs(client, [{"identifier": "disability", "value": "Yes"}])
    disability_no, disability_no_total = collect_slugs(client, [{"identifier": "disability", "value": "No"}])
    student_yes, _ = collect_slugs(client, [{"identifier": "isStudent", "value": "Yes"}])
    student_no, _ = collect_slugs(client, [{"identifier": "isStudent", "value": "No"}])
    bpl_yes, _ = collect_slugs(client, [{"identifier": "isBpl", "value": "Yes"}])
    bpl_no, _ = collect_slugs(client, [{"identifier": "isBpl", "value": "No"}])
    print(
        f"  disability yes {len(disability_yes)}/{disability_yes_total} no {len(disability_no)}/{disability_no_total}",
        flush=True,
    )

    print("Scanning age coverage", flush=True)
    ages = {slug: set() for slug in selected_slugs}
    selected_set = set(selected_slugs)

    def scan_age(age):
        slugs, total = collect_slugs(
            client, [{"identifier": "age-general", "min": age, "max": age}]
        )
        return age, slugs, total

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(scan_age, age) for age in TEST_AGES]
        for future in as_completed(futures):
            age, slugs, total = future.result()
            print(f"  age {age}: {len(slugs)}/{total}", flush=True)
            if total and len(slugs) < total * 0.98:
                raise RuntimeError(f"Incomplete age scan {age}")
            for slug in selected_set.intersection(slugs):
                ages[slug].add(age)

    facet_bundle = {
        "gender": gender,
        "caste": caste,
        "residence": residence,
        "occupation": occupation,
        "employment": employment,
        "disability_yes": disability_yes,
        "disability_no": disability_no,
        "student_yes": student_yes,
        "student_no": student_no,
        "bpl_yes": bpl_yes,
        "bpl_no": bpl_no,
        "ages": ages,
    }

    print("Fetching scheme details", flush=True)
    schemes = []
    failures = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        future_map = {
            pool.submit(build_scheme, client, record, facet_bundle): record["slug"] for record in selected
        }
        done = 0
        for future in as_completed(future_map):
            slug = future_map[future]
            done += 1
            try:
                schemes.append(future.result())
            except Exception as error:  # noqa: BLE001
                failures.append({"slug": slug, "error": str(error)})
                print(f"  fail {slug}: {error}", flush=True)
            if done % 20 == 0:
                print(f"  details {done}/{len(selected)}", flush=True)
    schemes.sort(key=lambda scheme: scheme["name"]["en"].lower())
    payload = {
        "meta": {
            "source": "https://www.myscheme.gov.in/",
            "api": "https://api.myscheme.gov.in/search/v6/schemes",
            "lastVerified": LAST_VERIFIED,
            "disclaimer": "Copied from the official myScheme portal. Not a government site.",
            "states": states,
            "categories": categories,
            "count": len(schemes),
            "failures": failures,
        },
        "schemes": schemes,
    }
    with open(OUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"Wrote {len(schemes)} schemes to {OUT_PATH}", flush=True)
    if len(schemes) < 150:
        print("Fewer than 150 schemes", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
