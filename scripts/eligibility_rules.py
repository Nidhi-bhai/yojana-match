"""Turn official names and eligibility sentences into structured matcher fields.

A sentence is stored beside the field it supports. Nothing is filled in when the
official text does not state it.
"""

from __future__ import annotations

import re

from scheme_text import clean_text, income_ceiling

STUDENT_NAME_RE = re.compile(
    r"scholarship|\bstudents?\b|pre[-\s]?matric|post[-\s]?matric",
    re.I,
)
WIDOW_NAME_RE = re.compile(r"\bwidows?\b", re.I)
DAUGHTER_OF_WIDOW_RE = re.compile(r"daughter|girl", re.I)
EX_SERVICE_RE = re.compile(r"ex[-\s]?servicem", re.I)
FREEDOM_RE = re.compile(r"freedom fighter|swatantrata sainik", re.I)
ORPHAN_RE = re.compile(
    r"\borphan\b|died due to Covid|ward of Armed Forces|Paramilitary Forces martyred",
    re.I,
)
POLICE_WARD_RE = re.compile(
    r"wards?/widows of central police|central police force|police force personnel|"
    r"\bCPF\b|\bCAPF\b",
    re.I,
)
LISTING_RE = re.compile(
    r"\bSECC\b|Antyodaya|Priority Household|\bration card\b|deprivation criteria|"
    r"below (?:the )?poverty line|\bBPL\b|family card",
    re.I,
)
LISTING_DETAIL_RE = re.compile(
    r"\bSECC\b|Antyodaya|Priority Household|\bration card\b|deprivation criteria|family card",
    re.I,
)
AGE_MAX_RE = re.compile(
    r"(?:not more than|not be more than|below|under|less than|up to|upto)\s*"
    r"(?:the age of\s*)?(\d{1,2})\s*years",
    re.I,
)

# Extra conditions the eight answers cannot settle. The quote is the official sentence.
UNCERTAIN_PATTERNS = [
    ("bank-account", re.compile(r"bank account holder|have a (?:savings )?bank account|having a bank account", re.I)),
    ("merit", re.compile(r"top\s*1\s*%|\bmarks\b|grade point|\d+\s*%|JEE|AIPMT", re.I)),
    ("course", re.compile(r"pre[-\s]?matric|post[-\s]?matric|class\s*[0-9]|currently studying|regular student|\bdiploma\b|\bdegree\b", re.I)),
    ("institution", re.compile(r"\binstitution\b|\buniversity\b|recognized school|\bAICTE\b|\bITI\b|philately|admitted to", re.I)),
    ("land", re.compile(r"landholding|cultivable land|land holding|acres of land|land record|land ownership|owner cultivator", re.I)),
    ("enterprise", re.compile(r"greenfield|new project|new enterprise", re.I)),
    ("qualification", re.compile(r"\bpharma\b|pharmacist|educational qualification|VIII standard|class 10 pass", re.I)),
    ("organisation", re.compile(r"industry partner|annual turnover|employee strength", re.I)),
    ("pregnancy", re.compile(r"pregnan|lactating|maternity", re.I)),
    ("trade", re.compile(r"construction worker|weavers?|fisherm[ae]n|\bfishers?\b|\bartisans?\b|handloom", re.I)),
    ("place", re.compile(r"\bhabitation\b|revenue village", re.I)),
    ("income-bands", re.compile(r"Economically Weaker Section|Middle Income Group|Low Income Group", re.I)),
    ("job-role", re.compile(r"job role|course curriculum", re.I)),
    ("region", re.compile(r"North Eastern States|Union Territories", re.I)),
    ("lpg", re.compile(r"LPG connection", re.I)),
    ("voter", re.compile(r"voter list", re.I)),
    ("other-benefit", re.compile(r"not be allowed to avail|already availed|shall not be allowed to avail|not be Recipient|not be a beneficiary|not be a recipient|any other .{0,40}pension", re.I)),
    ("disability-degree", re.compile(r"80\s*%|40\s*%|disability of\s+\d+", re.I)),
    ("family", re.compile(r"daughter of|orphan girls?|remarriage|marriage assistance|children of", re.I)),
    ("identity", re.compile(r"\bunmarried\b|\bdestitute\b|minority community|girl child|Self-Help Group|retired government|cluster housing", re.I)),
]


def _sentences(text):
    cleaned = clean_text(text)
    if not cleaned:
        return []
    parts = re.split(r"[\n]+|(?<=\.)\s+", cleaned)
    sentences = []
    for part in parts:
        sentence = " ".join(part.split())
        if len(sentence) >= 12:
            sentences.append(sentence[:280])
    return sentences


def _first_quote(sentences, pattern):
    for sentence in sentences:
        if pattern.search(sentence):
            return sentence
    return ""


def annotate_scheme(scheme):
    """Add structured eligibility fields. Returns the same scheme."""
    criteria = dict(scheme.get("criteria") or {})
    name = ((scheme.get("name") or {}).get("en")) or ""
    eligibility = ((scheme.get("eligibility") or {}).get("en")) or ""
    sentences = _sentences(eligibility)

    if STUDENT_NAME_RE.search(name):
        criteria["studentOnly"] = True
        criteria["studentQuote"] = name.strip()[:240]

    occupations = criteria.get("occupations") or []
    occupation_open = not occupations or occupations == ["All"]
    if occupation_open:
        farmer = _first_quote(sentences, re.compile(r"resident farmer|must be a farmer|should be a farmer", re.I))
        if farmer:
            criteria["occupations"] = ["Farmer"]
            criteria["occupationQuote"] = farmer

    if criteria.get("ageMin") in (None, ""):
        for sentence in sentences:
            match = re.search(
                r"age (?:should|must|shall) be (\d{1,3}) years (?:and above|or above|or more)",
                sentence,
                re.I,
            )
            if match:
                criteria["ageMin"] = int(match.group(1))
                criteria["ageMinQuote"] = sentence
                break

    if re.search(r"pre[-\s]?matric", name, re.I) and criteria.get("ageMax") in (None, ""):
        for sentence in sentences:
            if not re.search(r"\bage\b", sentence, re.I):
                continue
            match = AGE_MAX_RE.search(sentence)
            if not match:
                continue
            age = int(match.group(1))
            if 10 <= age <= 25:
                criteria["ageMax"] = age
                criteria["ageMaxQuote"] = sentence
                break

    groups = []
    group_quotes = []
    widow_name = bool(WIDOW_NAME_RE.search(name))
    daughter_scheme = bool(widow_name and DAUGHTER_OF_WIDOW_RE.search(name))
    if FREEDOM_RE.search(name) or FREEDOM_RE.search(eligibility[:700]):
        groups.append("freedom-fighter")
        group_quotes.append(_first_quote(sentences, FREEDOM_RE) or name)
    if EX_SERVICE_RE.search(name) or EX_SERVICE_RE.search(eligibility[:500]):
        groups.append("ex-serviceman")
        group_quotes.append(_first_quote(sentences, EX_SERVICE_RE) or name)
    if widow_name and not daughter_scheme and not POLICE_WARD_RE.search(name):
        groups.append("widow")
        group_quotes.append(name.strip()[:240])
    if re.search(r"candidate should be one of the following", eligibility, re.I) and re.search(
        r"\borphan\b", eligibility, re.I
    ):
        groups.append("orphan")
        group_quotes.append(_first_quote(sentences, re.compile(r"orphan", re.I)))
    elif re.search(r"\borphans?\b", name, re.I) and not daughter_scheme:
        groups.append("orphan")
        group_quotes.append(name.strip()[:240])
    if POLICE_WARD_RE.search(name):
        groups.append("police-ward")
        group_quotes.append(name.strip()[:240])

    # "Widow of an ex-serviceman" means both. "Ex-servicemen and their widows" means either.
    if "widow" in groups and "ex-serviceman" in groups and re.search(r"widow of ex", name, re.I):
        criteria["specialGroupMode"] = "all"
    else:
        criteria["specialGroupMode"] = "any"
    criteria["specialGroups"] = groups
    criteria["specialGroupQuote"] = " ".join(quote for quote in group_quotes if quote)[:400]

    listing = bool(criteria.get("bplOnly")) or bool(LISTING_RE.search(eligibility))
    criteria["listingRequired"] = listing
    criteria["listingDetail"] = bool(LISTING_DETAIL_RE.search(eligibility))
    criteria["listingQuote"] = _first_quote(sentences, LISTING_RE)

    amount, note = income_ceiling(eligibility)
    if amount is not None:
        criteria["incomeCeilingInr"] = amount
        criteria["incomeCeilingNote"] = note

    uncertain = []
    seen = set()
    for code, pattern in UNCERTAIN_PATTERNS:
        quote = _first_quote(sentences, pattern)
        if not quote or code in seen:
            continue
        seen.add(code)
        uncertain.append({"code": code, "quote": quote})
    if criteria.get("studentOnly") and not any(item["code"] == "course" for item in uncertain):
        uncertain.append({"code": "course", "quote": name.strip()[:240]})
    criteria["uncertain"] = uncertain[:8]

    scheme["criteria"] = criteria
    _pmuy_note(scheme)
    return scheme


def _pmuy_note(scheme):
    """Keep myScheme's close date, and point the 2.0 text at the open record."""
    if scheme.get("slug") != "pmuy":
        return
    eligibility = ((scheme.get("eligibility") or {}).get("en")) or ""
    if scheme.get("closeDate") == "2021-09-30" and re.search(r"UJJWALA\s*2\.0", eligibility, re.I):
        scheme["closeDateNote"] = (
            "myScheme lists 2021-09-30 as the close date on this record, but the eligibility "
            "text describes Ujjwala 2.0. Ujjwala 2.0 is the separate myScheme record "
            "Pradhan Mantri Ujjwala Yojana 2.0, which has no close date. This record stays "
            "closed and is not offered as a match."
        )
