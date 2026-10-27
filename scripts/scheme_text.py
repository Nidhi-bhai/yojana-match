"""Clean myScheme rich text and copy only amounts the official text states."""

import html
import re

CURRENCY_RE = re.compile(r"(₹|Rs\.?|INR)\s*[0-9]")
INCOME_SENTENCE_RE = re.compile(r"income", re.I)
INCOME_RELATION_RE = re.compile(
    r"(does not exceed|do not exceed|shall not exceed|should not exceed|must not exceed|"
    r"not exceed|not more than|no more than|less than|below|up to|upto|ceiling|"
    r"or less|or below|within)",
    re.I,
)
AMOUNT_RE = re.compile(
    r"(?:₹|Rs\.?|INR)\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(lakh|lakhs|lac|crore|crores)?",
    re.I,
)
MALE_SC_ST_RE = re.compile(
    r"if the applicant is a male, he must be from SC\s*/\s*ST category",
    re.I,
)


def clean_text(value):
    if not value or not isinstance(value, str):
        return ""
    text = value.replace("\r", "")
    for _ in range(3):
        unescaped = html.unescape(text)
        if unescaped == text:
            break
        text = unescaped
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def slate_to_text(node):
    parts = []

    def walk(item):
        if isinstance(item, dict):
            if isinstance(item.get("text"), str):
                parts.append(item["text"])
            for child in item.get("children") or []:
                walk(child)
            kind = item.get("type") or ""
            if kind in ("paragraph", "list_item", "align_justify"):
                parts.append("\n")
        elif isinstance(item, list):
            for child in item:
                walk(child)

    walk(node)
    return clean_text("".join(parts))


def document_lines(block):
    if not isinstance(block, dict):
        return []
    text = slate_to_text(block.get("documents_required"))
    if not text:
        text = clean_text(block.get("documentsRequired_md") or "")
    lines = []
    for raw in text.splitlines():
        line = raw.strip(" \t-*•")
        line = re.sub(r"^\d+\.\s*", "", line).strip()
        if len(line) < 2:
            continue
        if line not in lines:
            lines.append(line)
    return lines


def _money_lines(text):
    lines = []
    for raw in text.splitlines():
        line = raw.strip(" \t-*•>")
        line = re.sub(r"^\d+\.\s*", "", line).strip()
        line = re.sub(r"\s{2,}", " ", line)
        if not line or not CURRENCY_RE.search(line):
            continue
        if len(line) > 280:
            continue
        if line not in lines:
            lines.append(line)
    return lines


def benefit_amount(text):
    """Return one official benefit line when the page states a single amount line.

    Multiple different amount lines are left blank so we do not pick a figure
    the page did not single out. The full benefits text is still shown.
    """
    lines = _money_lines(clean_text(text))
    if len(lines) == 1:
        return lines[0]
    return ""


def _to_inr(number, unit):
    value = float(number.replace(",", ""))
    unit = (unit or "").lower()
    if unit in ("lakh", "lakhs", "lac"):
        value *= 100000
    elif unit in ("crore", "crores"):
        value *= 10000000
    if value <= 0:
        return None
    return int(round(value))


def income_ceiling(text):
    """Parse an annual income ceiling only from a sentence that states one.

    Returns (amount_inr or None, verbatim sentence).
    """
    cleaned = clean_text(text)
    if not cleaned:
        return None, ""
    chunks = re.split(r"[\n]+|(?<=\.)\s+", cleaned)
    found = []
    for chunk in chunks:
        sentence = " ".join(chunk.split())
        if len(sentence) < 12 or len(sentence) > 400:
            continue
        if not INCOME_SENTENCE_RE.search(sentence):
            continue
        if not INCOME_RELATION_RE.search(sentence):
            continue
        amounts = []
        for match in AMOUNT_RE.finditer(sentence):
            amount = _to_inr(match.group(1), match.group(2))
            if amount and 1000 <= amount <= 100000000:
                amounts.append(amount)
        if len(amounts) != 1:
            continue
        amount = amounts[0]
        monthly = bool(re.search(r"per month|a month|monthly|p\.m\.", sentence, re.I))
        annual = bool(re.search(r"per annum|annual|yearly|p\.a\.|every year", sentence, re.I))
        if monthly and annual:
            continue
        if monthly and not annual:
            amount *= 12
        found.append((amount, sentence))
    amounts_near_income = []
    for chunk in chunks:
        sentence = " ".join(chunk.split())
        if not INCOME_SENTENCE_RE.search(sentence):
            continue
        for match in AMOUNT_RE.finditer(sentence):
            amount = _to_inr(match.group(1), match.group(2))
            if amount and 1000 <= amount <= 100000000:
                amounts_near_income.append(amount)
    if len(set(amounts_near_income)) > 1:
        return None, ""
    if not found:
        return None, ""
    unique = {item[0] for item in found}
    if len(unique) != 1:
        return None, ""
    sentence = found[0][1]
    if re.search(
        r"OBC or EWS|if from the APL|Above Poverty Line|for boys|not applicable",
        sentence,
        re.I,
    ):
        return None, ""
    return found[0]


FARMER_RE = re.compile(
    r"(?:^|\n)\s*(?:\d+\.\s*|\-\s*)?(?:all\s+)?(?:landholding\s+)?farmers?\b"
    r"|the applicant must be a farmer"
    r"|applicant must be a farmer",
    re.I,
)


DISABILITY_REQUIRED_RE = re.compile(
    r"(?:partially|permanently)?\s*disabled due to[^\n.]{0,140}",
    re.I,
)


def disability_required_quote(text):
    """Quote an eligibility line that requires the applicant to be disabled."""
    cleaned = clean_text(text)
    match = DISABILITY_REQUIRED_RE.search(cleaned)
    if not match:
        return ""
    return " ".join(match.group(0).split())


def enrich_criteria(criteria, eligibility):
    """Fill structured fields only from sentences the official text states."""
    amount, note = income_ceiling(eligibility)
    criteria["incomeCeilingInr"] = amount
    criteria["incomeCeilingNote"] = note
    if not criteria.get("occupations"):
        quote = farmer_quote(eligibility)
        if quote:
            criteria["occupations"] = ["Farmer"]
            criteria["occupationQuote"] = quote
    if criteria.get("disability") != "Yes":
        quote = disability_required_quote(eligibility)
        if quote:
            criteria["disability"] = "Yes"
            criteria["disabilityQuote"] = quote
    return criteria


def farmer_quote(text):
    """Return the official sentence when the scheme is only for farmers."""
    cleaned = clean_text(text)
    if not cleaned:
        return ""
    match = FARMER_RE.search(cleaned)
    if not match:
        return ""
    start = cleaned.rfind("\n", 0, match.start()) + 1
    end = cleaned.find("\n", match.end())
    if end == -1:
        end = len(cleaned)
    return " ".join(cleaned[start:end].split())[:240]


def male_must_be_sc_st(text):
    cleaned = clean_text(text)
    match = MALE_SC_ST_RE.search(cleaned)
    if not match:
        return ""
    return match.group(0)


def age_bounds(covered, tested_ages):
    """Turn official age-filter hits into a closed range.

    A missing sample on either end means that end is open. A gap in the
    middle means the range is not a single window, so no age filter is applied.
    """
    if not covered:
        return None, None
    tested = list(tested_ages)
    covered_set = set(covered)
    runs = []
    current = []
    for age in tested:
        if age in covered_set:
            current.append(age)
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    if len(runs) != 1:
        return None, None
    block = runs[0]
    age_min = None if block[0] == tested[0] else block[0]
    age_max = None if block[-1] == tested[-1] else block[-1]
    return age_min, age_max
