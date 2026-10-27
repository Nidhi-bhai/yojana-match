#!/usr/bin/env python3
"""Generate the GitHub Pages site in docs/ from data/schemes.json."""

from __future__ import annotations

import html
import json
import os
import re
import shutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_PATH = os.path.join(ROOT, "data", "schemes.json")
DOCS = os.path.join(ROOT, "docs")
SITE = "https://nidhi-bhai.github.io/yojana-match"
DISCLAIMER = (
    "YojanaMatch is not a government website. Names, benefits, eligibility, and links "
    "are copied from official portals and can change. Confirm every scheme on the official "
    "source before you apply."
)
AS_OF = "2026-10-27"
BRAND = " | YojanaMatch"


def clip(text, limit):
    text = re.sub(r"\s+", " ", "" if text is None else str(text)).strip()
    if len(text) <= limit:
        return text
    trimmed = text[: limit + 1]
    if " " in trimmed:
        trimmed = trimmed.rsplit(" ", 1)[0]
    trimmed = trimmed.rstrip(" .,:;|-—")
    if len(trimmed) < 20:
        trimmed = text[:limit].rstrip()
    return trimmed


def brand_title(core):
    core = re.sub(r"\s*\|\s*YojanaMatch$", "", re.sub(r"\s+", " ", core).strip())
    if len(core) + len(BRAND) <= 60:
        return core + BRAND
    return clip(core, 60 - len(BRAND)) + BRAND


def fit_title(title):
    title = re.sub(r"\s+", " ", title).strip()
    if title.startswith("YojanaMatch"):
        return clip(title, 60)
    return brand_title(title)


def scheme_core(scheme):
    short = (scheme.get("shortTitle") or "").strip()
    name = scheme["name"]["en"].strip()

    def marked(label):
        if re.search(r"diploma", name, re.I) and not re.search(r"diploma", label, re.I):
            return f"{label} Diploma"
        if re.search(r"degree", name, re.I) and not re.search(r"degree", label, re.I):
            return f"{label} Degree"
        return label

    labels = [marked(name)]
    if short and marked(short) not in labels:
        labels.append(marked(short))
    tails = (
        ": eligibility, documents, how to apply",
        ": eligibility and documents",
        ": eligibility",
    )
    for label in labels:
        for tail in tails:
            core = label + tail
            if len(core) + len(BRAND) <= 60:
                return core
    fallback = marked(short or name)
    return clip(fallback, 60 - len(BRAND) - len(": eligibility")) + ": eligibility"


def scheme_description(scheme):
    name = scheme["name"]["en"].strip()
    benefit = (scheme.get("benefitAmount") or "").strip()
    marker = ""
    if re.search(r"diploma", name, re.I):
        marker = " Diploma."
    elif re.search(r"degree", name, re.I):
        marker = " Degree."
    benefit_bit = f" Benefit: {clip(benefit, 48)}." if benefit else ""
    text = (
        f"Who can apply for {name}.{marker}{benefit_bit} "
        "Documents and the official apply link. Unofficial; verify on myScheme."
    )
    return clip(text, 155)


def esc(value):
    return html.escape("" if value is None else str(value), quote=True)


def slugify(label):
    text = label.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "scheme"


def json_for_script(payload):
    return json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")


def rel(depth, path):
    return ("../" * depth) + path


def paragraphs(text):
    blocks = [part.strip() for part in (text or "").split("\n") if part.strip()]
    if not blocks:
        return ""
    return "\n".join(f"<p>{esc(part)}</p>" for part in blocks)


def chrome(depth):
    home = rel(depth, "index.html")
    schemes = rel(depth, "schemes/index.html")
    about = rel(depth, "about/index.html")
    css = rel(depth, "css/styles.css")
    icon = rel(depth, "favicon.svg")
    return css, icon, f"""
    <a class="skip" href="#content">Skip to content</a>
    <header class="site-header">
      <a class="brand" href="{home}">Yojana<span>Match</span></a>
      <nav class="header-nav" aria-label="Primary">
        <a href="{schemes}" data-i18n="allSchemes">All schemes</a>
        <a href="{about}" data-i18n="about">How this works</a>
        <div class="lang" role="group" aria-label="Language">
          <button type="button" data-lang="en" aria-pressed="true">EN</button>
          <button type="button" data-lang="hi" lang="hi">हिं</button>
          <button type="button" data-lang="te" lang="te">తె</button>
        </div>
      </nav>
    </header>
    <p class="disclaimer" data-i18n="disclaimer">{esc(DISCLAIMER)}</p>
    <p class="disclaimer te-note" data-i18n="teBeta" hidden>Telugu scheme text is a machine translation (beta). Check the English.</p>
    """


def footer():
    return """
    <footer class="site-footer">
      <p><a href="https://github.com/Nidhi-bhai" data-i18n="footerBuilt">Built by Nidhi Karuturi</a></p>
    </footer>
    """


def page(title, description, canonical, depth, body, extra_head="", scripts=""):
    css, icon, head = chrome(depth)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(fit_title(title))}</title>
  <meta name="description" content="{esc(clip(description, 155))}">
  <link rel="canonical" href="{esc(canonical)}">
  <meta property="og:title" content="{esc(fit_title(title))}">
  <meta property="og:description" content="{esc(clip(description, 155))}">
  <meta property="og:url" content="{esc(canonical)}">
  <meta property="og:type" content="website">
  <meta name="theme-color" content="#0e4d3c">
  <link rel="icon" href="{icon}" type="image/svg+xml">
  <link rel="stylesheet" href="{css}">
  {extra_head}
</head>
<body>
  {head}
  <main id="content">
    {body}
  </main>
  {footer()}
  {scripts}
</body>
</html>
"""


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def option(value, label, selected=False):
    sel = " selected" if selected else ""
    extra = f' data-i18n="{esc(value)}"' if value in {
        "under-1l", "1-2.5l", "2.5-5l", "5-8l", "above-8l",
        "farmer", "student", "msme", "woman_entrepreneur", "salaried", "unemployed", "other",
        "general", "obc", "sc", "st", "pvtg", "dnt",
    } else ""
    return f'<option value="{esc(value)}"{extra}{sel}>{esc(label)}</option>'


def index_page(payload, categories, states):
    covered = {label for label, _slug in states}
    names = list(payload["meta"]["states"])
    for label, _slug in states:
        if label not in names:
            names.append(label)
    state_options = ['<option value="">Choose</option>']
    for state in names:
        if state in covered:
            state_options.append(option(state, state))
        else:
            state_options.append(
                f'<option value="{esc(state)}" data-central-only="true">{esc(state)} (central schemes only)</option>'
            )
    category_links = " ".join(
        f'<a href="category/{esc(slug)}/">{esc(label)}</a>' for label, slug in categories
    )
    state_links = " ".join(
        f'<a href="state/{esc(slug)}/">{esc(label)}</a>' for label, slug in states
    )
    body = f"""
    <p class="lede" data-i18n="tagline">See which of 239 central and state schemes may fit you.</p>
    <h1>Which government scheme am I eligible for?</h1>
    <p id="loading" data-i18n="loading">Loading the scheme database…</p>
    <form id="matcher-form" class="panel">
      <div class="questions">
        <div>
          <label for="state" data-i18n="qState">Which state do you live in?</label>
          <select id="state" name="state" required>{''.join(state_options)}</select>
          <span class="hint" data-i18n="stateHint">A state marked central schemes only has no state scheme in this list yet. Central schemes are still matched.</span>
        </div>
        <div>
          <label for="age" data-i18n="qAge">What is your age?</label>
          <span class="hint" data-i18n="ageHint">Completed years</span>
          <input id="age" name="age" type="number" inputmode="numeric" min="0" max="120" required>
        </div>
        <div>
          <label for="gender" data-i18n="qGender">Gender</label>
          <select id="gender" name="gender" required>
            <option value="">Choose</option>
            <option value="Female" data-i18n="optFemale">Female</option>
            <option value="Male" data-i18n="optMale">Male</option>
            <option value="Transgender" data-i18n="optTrans">Transgender</option>
          </select>
        </div>
        <div>
          <label for="income" data-i18n="qIncome">Annual family income</label>
          <select id="income" name="income" required>
            <option value="">Choose</option>
            {option("under-1l", "Under ₹1,00,000")}
            {option("1-2.5l", "₹1,00,000 – ₹2,50,000")}
            {option("2.5-5l", "₹2,50,000 – ₹5,00,000")}
            {option("5-8l", "₹5,00,000 – ₹8,00,000")}
            {option("above-8l", "Above ₹8,00,000")}
          </select>
        </div>
        <div>
          <label for="occupation" data-i18n="qOccupation">Occupation</label>
          <select id="occupation" name="occupation" required>
            <option value="">Choose</option>
            {option("farmer", "Farmer")}
            {option("student", "Student")}
            {option("msme", "MSME / self-employed")}
            {option("woman_entrepreneur", "Woman entrepreneur")}
            {option("salaried", "Salaried")}
            {option("unemployed", "Unemployed")}
            {option("other", "Other")}
          </select>
        </div>
        <div>
          <label for="caste" data-i18n="qCaste">Category</label>
          <select id="caste" name="caste" required>
            <option value="">Choose</option>
            {option("general", "General")}
            {option("obc", "Other Backward Class (OBC)")}
            {option("sc", "Scheduled Caste (SC)")}
            {option("st", "Scheduled Tribe (ST)")}
            {option("pvtg", "Particularly Vulnerable Tribal Group (PVTG)")}
            {option("dnt", "De-notified, nomadic, and semi-nomadic (DNT)")}
          </select>
        </div>
        <fieldset>
          <legend data-i18n="qDisability">Do you have a disability?</legend>
          <div class="choices">
            <label><input type="radio" name="disability" value="yes" required> <span data-i18n="disabilityYes">Yes</span></label>
            <label><input type="radio" name="disability" value="no"> <span data-i18n="disabilityNo">No</span></label>
          </div>
        </fieldset>
        <fieldset>
          <legend data-i18n="qResidence">Where do you live?</legend>
          <div class="choices">
            <label><input type="radio" name="residence" value="Rural" required> <span data-i18n="Rural">Rural</span></label>
            <label><input type="radio" name="residence" value="Urban"> <span data-i18n="Urban">Urban</span></label>
          </div>
        </fieldset>
        <fieldset class="span-2">
          <legend data-i18n="qGroups">Do any of these describe you? Leave this blank if none do.</legend>
          <div class="choices stack">
            <label><input type="checkbox" name="group" value="ex-serviceman"> <span data-i18n="gEx">Ex-serviceman, or widow of an ex-serviceman</span></label>
            <label><input type="checkbox" name="group" value="freedom-fighter"> <span data-i18n="gFreedom">Freedom fighter, or an eligible dependent</span></label>
            <label><input type="checkbox" name="group" value="orphan"> <span data-i18n="gOrphan">Orphan, lost a parent to Covid-19, or ward of a martyred armed-forces or paramilitary member</span></label>
            <label><input type="checkbox" name="group" value="widow"> <span data-i18n="gWidow">Widow</span></label>
            <label><input type="checkbox" name="group" value="police-ward"> <span data-i18n="gPolice">Ward or widow of police or Central Armed Police Forces personnel</span></label>
          </div>
        </fieldset>
        <fieldset class="span-2">
          <legend data-i18n="qListing">Are you on a ration card (AAY or PHH), a family card, or an SECC / below-poverty-line list?</legend>
          <div class="choices">
            <label><input type="radio" name="listing" value="yes" required> <span data-i18n="listingYes">Yes</span></label>
            <label><input type="radio" name="listing" value="no"> <span data-i18n="listingNo">No</span></label>
            <label><input type="radio" name="listing" value="not-sure"> <span data-i18n="listingUnsure">Not sure</span></label>
          </div>
        </fieldset>
      </div>
      <p id="form-error" class="form-error" role="alert"></p>
      <button class="primary" type="submit" data-i18n="submit">Show my schemes</button>
    </form>
    <div class="toolbar">
      <label class="hint" for="result-filter">Show
        <select id="result-filter">
          <option value="all" data-i18n="filterAll">All matches</option>
          <option value="state" data-i18n="groupState">Schemes for your state</option>
          <option value="central" data-i18n="groupCentral">Central schemes</option>
        </select>
      </label>
      <label class="hint" for="result-search"><span data-i18n="searchResults">Search within matches</span>
        <input id="result-search" type="search">
      </label>
    </div>
    <section id="results" aria-live="polite"></section>
    <section class="help-pack" id="help-pack">
      <h2 data-i18n="helpTitle">Application help pack</h2>
      <p class="price">$2</p>
      <p data-i18n="helpBody">Optional $2 PDF of your confirmed matches: documents, apply link, and source. It is the same checklist already shown free on this page. It is in English. It is not a form-filling service and it does not guarantee approval.</p>
      <p data-i18n="helpFree">PayPal can't take payments from buyers in India. The full checklist is free on this page.</p>
      <p data-i18n="helpEnglish">The PDF is in English.</p>
      <p data-i18n="helpRefund">For a refund, email nidhi69n@gmail.com with your PayPal order id.</p>
      <div id="paypal-button"></div>
      <p id="paypal-note" data-i18n="helpNeedsMatch">Answer the questions first. The PDF lists only confirmed matches.</p>
      <div id="saved-orders"></div>
    </section>
    <section class="browse">
      <h2 data-i18n="browseTitle">Browse schemes</h2>
      <p data-i18n="browseIntro">These pages are copied from myScheme. This is a subset, not every scheme in India.</p>
      <h3 data-i18n="categories">Categories</h3>
      <div class="chip-row">{category_links}</div>
      <h3 data-i18n="states">States</h3>
      <div class="chip-row">{state_links}</div>
    </section>
    """
    scripts = """
    <script src="config.js"></script>
    <script src="js/i18n.js"></script>
    <script src="js/match.js"></script>
    <script src="js/pdf.js"></script>
    <script src="js/app.js"></script>
    """
    description = (
        "Answer 10 questions and see which of 239 copied schemes may fit. "
        "Documents and official links. Unofficial; verify on myScheme."
    )
    return page(
        "YojanaMatch — which government scheme am I eligible for?",
        description,
        SITE + "/",
        0,
        body,
        scripts=scripts,
    )


def scheme_page(scheme, related):
    name = scheme["name"]["en"]
    brief = scheme["brief"]["en"]
    title = scheme_core(scheme)
    description = scheme_description(scheme)
    canonical = f"{SITE}/schemes/{scheme['slug']}/"
    benefit = scheme.get("benefitAmount") or "Benefit amount not stated on the official page"
    docs = "".join(f"<li>{esc(item)}</li>" for item in scheme["documents"].get("en") or [])
    if not docs:
        docs = "<li>Documents were not listed on the official page.</li>"
    apply_links = scheme.get("applyLinks") or []
    if apply_links:
        apply_html = "".join(
            f'<p><a class="button" href="{esc(link["url"])}" rel="noopener noreferrer">{esc(link.get("mode") or "Apply on the official site")}</a></p>'
            for link in apply_links
        )
    else:
        apply_html = "<p>Official apply link was not listed.</p>"
    refs = "".join(
        f'<li><a href="{esc(item["url"])}" rel="noopener noreferrer">{esc(item.get("title") or item["url"])}</a></li>'
        for item in scheme.get("references") or []
    )
    related_html = "".join(
        f'<li><a href="../{esc(item["slug"])}/">{esc(item["name"]["en"])}</a></li>' for item in related
    )
    states = ", ".join(scheme.get("states") or [])
    categories = ", ".join(scheme.get("categories") or [])
    hi = scheme["name"].get("hi") or ""
    te = scheme["name"].get("te") or ""
    alt = ""
    if hi:
        alt += f'<span lang="hi">{esc(hi)}</span>'
    if te:
        alt += f' <span lang="te">{esc(te)}</span>'
    closed = bool(scheme.get("closeDate") and scheme["closeDate"] < AS_OF)
    close = ""
    if scheme.get("closeDate"):
        close = (
            f'<p class="note">myScheme close date: {esc(scheme["closeDate"])}. '
            "This scheme is excluded from matches and from the PDF.</p>"
            if closed
            else f'<p class="note">myScheme close date: {esc(scheme["closeDate"])}.</p>'
        )
    if scheme.get("closeDateNote"):
        close += f'<p class="note">{esc(scheme["closeDateNote"])}</p>'
    full_name = ""
    if name not in title:
        full_name = f'<p class="meta">{esc(name)}</p>'
    copy = {
        "name": scheme["name"],
        "brief": scheme["brief"],
        "benefits": scheme["benefits"],
        "eligibility": scheme["eligibility"],
        "howToApply": scheme["howToApply"],
        "benefitAmount": {"en": scheme.get("benefitAmount") or "", "hi": scheme.get("benefitAmount") or "", "te": scheme.get("benefitAmount") or ""},
        "documents": scheme["documents"],
    }
    graph = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "url": canonical,
        "description": description,
        "isPartOf": {"@type": "WebSite", "name": "YojanaMatch", "url": SITE + "/"},
        "mainEntity": {
            "@type": "GovernmentService",
            "name": name,
            "url": scheme["sourceUrl"],
            "serviceType": scheme.get("categories") or [],
            "provider": {
                "@type": "GovernmentOrganization",
                "name": scheme.get("ministry") or "Government of India",
            },
            "areaServed": "IN" if "All" in (scheme.get("states") or []) else scheme.get("states") or "IN",
        },
    }
    body = f"""
    <article class="prose">
      <p class="meta">{esc(scheme.get("level") or "")} · {esc(states)}</p>
      {('<p class="badge closed">Closed</p>' if closed else '')}
      <h1>{esc(title)}</h1>
      {full_name}
      <p class="alt-names">{alt}</p>
          <p data-scheme-block="brief">{esc(brief)}</p>
      <div class="scheme-layout">
        <div>
          <h2 data-i18n="benefits">Benefits</h2>
          <p class="benefit" data-scheme="benefitAmount">{esc(benefit)}</p>
          <div id="benefits-body" data-scheme-block="benefits">{paragraphs(scheme["benefits"]["en"])}</div>
          <h2 data-i18n="eligibility">Eligibility</h2>
          <div id="eligibility-body" data-scheme-block="eligibility">{paragraphs(scheme["eligibility"]["en"])}</div>
          <h2 data-i18n="documents">Documents</h2>
          <ul class="doc-list" id="document-list">{docs}</ul>
          <h2 data-i18n="howToApply">How to apply</h2>
          <div id="apply-body" data-scheme-block="howToApply">{paragraphs(scheme["howToApply"]["en"]) or "<p>Steps were not listed on the official page.</p>"}</div>
          {apply_html}
          {close}
          <p class="meta"><span data-i18n="verified">Copied from myScheme on</span> {esc(scheme["lastVerified"])}</p>
          <p><a href="{esc(scheme["sourceUrl"])}" rel="noopener noreferrer" data-i18n="source">Official source</a></p>
          {"<h2 data-i18n='references'>References on myScheme</h2><ul>" + refs + "</ul>" if refs else ""}
          <p><a href="../../index.html#matcher-form">Check this scheme against your answers</a></p>
        </div>
        <aside class="side">
          <div class="card">
            <p class="meta" data-i18n="ministry">Ministry</p>
            <p>{esc(scheme.get("ministry") or "—")}</p>
            <p class="meta">{esc(categories)}</p>
            <h2 data-i18n="related">Related schemes</h2>
            <ul>{related_html or "<li>—</li>"}</ul>
          </div>
        </aside>
      </div>
    </article>
    """
    scripts = f"""
    <script type="application/ld+json">{json_for_script(graph)}</script>
    <script type="application/json" id="scheme-copy">{json_for_script(copy)}</script>
    <script src="../../js/i18n.js"></script>
    <script src="../../js/scheme-page.js"></script>
    """
    # scheme-page.js will not rewrite benefits/eligibility blocks because they are
    # paragraphs. Add data-scheme on a visually hidden fallback? The toggle should
    # update the prose. Point data-scheme at the containers by using textContent,
    # which would flatten paragraphs. That is acceptable for the toggle.
    return page(title, description, canonical, 2, body, scripts=scripts)


def listing_page(title, description, canonical, depth, intro, items, crumb):
    links = "\n".join(
        f'<article class="card"><h2><a href="{esc(href)}">{esc(name)}</a></h2><p>{esc(brief)}</p><p class="meta">{esc(meta)}</p></article>'
        for href, name, brief, meta in items
    )
    body = f"<h1>{esc(title)}</h1><p>{esc(intro)}</p><p><a href=\"{crumb}\">YojanaMatch</a></p><div class=\"card-list\">{links}</div>"
    scripts = f'<script src="{rel(depth, "js/i18n.js")}"></script><script src="{rel(depth, "js/scheme-page.js")}"></script>'
    return page(title + " | YojanaMatch", description, canonical, depth, body, scripts=scripts)


def about_page():
    body = """
    <h1>How YojanaMatch works</h1>
    <p>YojanaMatch is an independent website built by Nidhi Karuturi. It is not a Government of India website and it is not a state government website.</p>
    <p>The database is a structured subset of schemes published on <a href="https://www.myscheme.gov.in/">myScheme</a>, the official scheme portal maintained for the Government of India. Each record keeps the official name, eligibility text, benefits text, documents, an apply link when myScheme lists one, the source URL, and the date the record was checked.</p>
    <p>If the official page does not state a single benefit amount, that field is left blank. Amounts are not estimated.</p>
    <p>The catalogue has 239 schemes copied from myScheme on 2026-10-27. It is a subset, not every scheme in India. “Copied from myScheme on” is the copy date, not a claim that every link was checked by hand.</p>
    <p>A scheme is confirmed only when every eligibility condition in the official text maps to a question the form asks: state, age, gender, category, occupation, disability, income band, and the optional questions for ex-servicemen, freedom fighters, orphans, widows, police wards, and ration card / SECC / below-poverty-line status. Scholarships are treated as student-only. A close date before 2026-10-27 removes the scheme from matches and from the PDF. Its page shows a closed badge.</p>
    <p>Where the official text states a further condition this form does not ask, the scheme is listed under “Possibly eligible, check conditions”. That section is not a match and it is not put in the PDF.</p>
    <p>The optional $2 PDF is the same English checklist already shown free on the page. PayPal can't take payments from buyers in India. The full checklist is free on the page. Email nidhi69n@gmail.com with the PayPal order id for a refund or a second copy.</p>
    <p lang="hi">योजनामैच सरकारी वेबसाइट नहीं है। आवेदन से पहले आधिकारिक स्रोत पर जाँच करें।</p>
    <p lang="te">యోజనామ్యాచ్ ప్రభుత్వ వెబ్‌సైట్ కాదు. దరఖాస్తుకు ముందు అధికారిక మూలంలో ధృవీకరించండి.</p>
    """
    scripts = '<script src="../js/i18n.js"></script><script src="../js/scheme-page.js"></script>'
    return page(
        "How YojanaMatch works",
        "How the YojanaMatch scheme database and eligibility matcher are sourced from myScheme.",
        SITE + "/about/",
        1,
        body,
        scripts=scripts,
    )


def not_found():
    body = "<h1>Page not found</h1><p><a href=\"index.html\">Back to YojanaMatch</a></p>"
    return page("Page not found", "That page is not on YojanaMatch.", SITE + "/", 0, body)


def main():
    with open(DATA_PATH, encoding="utf-8") as handle:
        payload = json.load(handle)
    schemes = payload["schemes"]
    if len(schemes) < 150:
        raise SystemExit(f"Need at least 150 schemes, found {len(schemes)}")
    i18n_path = os.path.join(DOCS, "js", "i18n.js")
    with open(i18n_path, encoding="utf-8") as handle:
        i18n_source = handle.read()
    if f"See which of {len(schemes)} central and state schemes may fit you." not in i18n_source:
        raise SystemExit("English tagline does not state the scheme count")
    descriptions = [scheme_description(scheme) for scheme in schemes]
    seen = {}
    for scheme, description in zip(schemes, descriptions):
        if len(description) > 155:
            raise SystemExit(f"Description too long for {scheme['slug']}")
        if len(fit_title(scheme_core(scheme))) > 60:
            raise SystemExit(f"Title too long for {scheme['slug']}")
        previous = seen.get(description)
        if previous:
            raise SystemExit(f"Duplicate description for {scheme['slug']} and {previous}")
        seen[description] = scheme["slug"]
    for folder in ("schemes", "category", "state", "about"):
        path = os.path.join(DOCS, folder)
        if os.path.isdir(path):
            shutil.rmtree(path)
    os.makedirs(os.path.join(DOCS, "data"), exist_ok=True)
    client_payload = {
        "meta": {key: value for key, value in payload["meta"].items() if key != "failures"},
        "schemes": [],
    }
    for scheme in schemes:
        client_scheme = dict(scheme)
        client_scheme.pop("howToApply", None)
        client_payload["schemes"].append(client_scheme)
    with open(os.path.join(DOCS, "data", "schemes.json"), "w", encoding="utf-8") as handle:
        json.dump(client_payload, handle, ensure_ascii=False, separators=(",", ":"))
        handle.write("\n")

    by_category = {}
    by_state = {}
    for scheme in schemes:
        for category in scheme.get("categories") or ["Uncategorised"]:
            by_category.setdefault(category, []).append(scheme)
        for state in scheme.get("states") or []:
            if state == "All":
                continue
            by_state.setdefault(state, []).append(scheme)
    categories = sorted((label, slugify(label)) for label in by_category)
    state_pages = sorted((label, slugify(label)) for label in by_state)
    used = set()
    for _, slug in categories + state_pages:
        if slug in used:
            raise SystemExit(f"Slug collision: {slug}")
        used.add(slug)

    write(os.path.join(DOCS, "index.html"), index_page(payload, categories, state_pages))
    write(os.path.join(DOCS, "about", "index.html"), about_page())
    write(os.path.join(DOCS, "404.html"), not_found())

    directory_items = []
    for scheme in schemes:
        brief = (scheme["brief"]["en"] or "")[:220]
        meta = f"{scheme.get('level') or ''} · Copied from myScheme on {scheme['lastVerified']}"
        directory_items.append((f"{scheme['slug']}/", scheme["name"]["en"], brief, meta))
        related = []
        for other in schemes:
            if other["slug"] == scheme["slug"]:
                continue
            if set(other.get("categories") or []).intersection(scheme.get("categories") or []):
                related.append(other)
            if len(related) == 6:
                break
        write(
            os.path.join(DOCS, "schemes", scheme["slug"], "index.html"),
            scheme_page(scheme, related),
        )
    write(
        os.path.join(DOCS, "schemes", "index.html"),
        listing_page(
            "All schemes",
            "Directory of government schemes in the YojanaMatch database, with eligibility and official sources.",
            SITE + "/schemes/",
            1,
            "Each scheme links to its eligibility, benefits, documents, and official source.",
            directory_items,
            "../index.html",
        ),
    )
    for label, slug in categories:
        items = []
        for scheme in sorted(by_category[label], key=lambda row: row["name"]["en"]):
            items.append(
                (
                    f"../../schemes/{scheme['slug']}/",
                    scheme["name"]["en"],
                    (scheme["brief"]["en"] or "")[:220],
                    scheme.get("level") or "",
                )
            )
        write(
            os.path.join(DOCS, "category", slug, "index.html"),
            listing_page(
                f"{label} schemes",
                f"{label} government schemes: eligibility, benefits, and how to apply.",
                f"{SITE}/category/{slug}/",
                2,
                f"Schemes filed under {label} on myScheme and copied into this subset.",
                items,
                "../../index.html",
            ),
        )
    for label, slug in state_pages:
        items = []
        for scheme in sorted(by_state[label], key=lambda row: row["name"]["en"]):
            items.append(
                (
                    f"../../schemes/{scheme['slug']}/",
                    scheme["name"]["en"],
                    (scheme["brief"]["en"] or "")[:220],
                    scheme.get("level") or "",
                )
            )
        write(
            os.path.join(DOCS, "state", slug, "index.html"),
            listing_page(
                f"{label} government schemes",
                f"Government schemes for {label}: eligibility, benefits, documents, and official links.",
                f"{SITE}/state/{slug}/",
                2,
                f"State schemes tagged for {label} on myScheme. Central schemes open to every state are on the home page matcher.",
                items,
                "../../index.html",
            ),
        )

    urls = [SITE + "/"]
    urls.append(SITE + "/about/")
    urls.append(SITE + "/schemes/")
    for scheme in schemes:
        urls.append(f"{SITE}/schemes/{scheme['slug']}/")
    for _, slug in categories:
        urls.append(f"{SITE}/category/{slug}/")
    for _, slug in state_pages:
        urls.append(f"{SITE}/state/{slug}/")
    body = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for url in urls:
        body.append("  <url>")
        body.append(f"    <loc>{esc(url)}</loc>")
        body.append("    <lastmod>2026-10-27</lastmod>")
        body.append("  </url>")
    body.append("</urlset>\n")
    write(os.path.join(DOCS, "sitemap.xml"), "\n".join(body))
    write(
        os.path.join(DOCS, "robots.txt"),
        "User-agent: *\nAllow: /\nSitemap: " + SITE + "/sitemap.xml\n",
    )
    write(os.path.join(DOCS, ".nojekyll"), "")
    print(f"Built {len(schemes)} scheme pages, {len(categories)} categories, {len(state_pages)} states")


if __name__ == "__main__":
    main()
