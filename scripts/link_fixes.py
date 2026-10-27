"""Replace apply and reference URLs that are dead or not official domains.

Replacements are official .gov.in / .nic.in pages that responded, or the scheme's
own myScheme page when no working official apply page was found. Amounts and
scheme names are not changed.
"""

from __future__ import annotations

import re

# Whole-string and in-prose replacements. Order matters.
EXACT_REPLACEMENTS = [
    (
        "https://pmkisan.gov.in/RegistrationFormnew.aspx",
        "https://pmkisan.gov.in/RegistrationFormupdated.aspx",
    ),
    (
        "https://scholarships.gov.in/fresh/newstdRegfrmInstruction",
        "https://scholarships.gov.in/",
    ),
    ("http://www.scholarships.gov.in/", "https://scholarships.gov.in/"),
    ("http://www.scholarships.gov.in", "https://scholarships.gov.in/"),
    ("http://janaushadhi.gov.in/Data/PMBJKs%20new%20form.pdf", "https://janaushadhi.gov.in/"),
    ("http://www.iari.res.in", "https://www.myscheme.gov.in/schemes/iaris"),
    ("https://www.iari.res.in/", "https://www.myscheme.gov.in/schemes/iaris"),
    ("https://www.iari.res.in", "https://www.myscheme.gov.in/schemes/iaris"),
]


def fix_url_string(text, slug):
    if not isinstance(text, str) or "http" not in text:
        return text
    for old, new in EXACT_REPLACEMENTS:
        text = text.replace(old, new)
    text = re.sub(r"https?://164\.100\.158\.73/\S*", "https://www.myscheme.gov.in/schemes/" + slug, text)
    text = re.sub(
        r"https://serviceonline-bihar-gov-in\.translate\.goog/\S*",
        "https://serviceonline.bihar.gov.in/",
        text,
    )
    text = re.sub(
        r"https?://(?:www\.)?pmkvyofficial\.org/\S*",
        "https://www.skillindiadigital.gov.in/",
        text,
    )
    text = re.sub(r"https?://(?:www\.)?cscindia\.info/?\S*", "https://pmaymis.gov.in/", text)
    text = re.sub(
        r"https?://(?:www\.)?janaushadhi\.gov\.in/Data/\S*",
        "https://janaushadhi.gov.in/",
        text,
    )
    if slug == "cmkvy":
        text = re.sub(
            r"https?://(?:www\.)?cgwcd\.gov\.in/\S*",
            "https://www.myscheme.gov.in/schemes/cmkvy",
            text,
        )
    return text


def _walk(value, slug):
    if isinstance(value, str):
        return fix_url_string(value, slug)
    if isinstance(value, list):
        return [_walk(item, slug) for item in value]
    if isinstance(value, dict):
        return {key: _walk(item, slug) for key, item in value.items()}
    return value


# Reference URLs that returned HTTP 404. They are removed. The scheme page still
# links to its myScheme record. Apply links are not in this list.
DEAD_REFERENCE_URLS = (
    "http://nadia.gov.in/DISHA/DISHASchemeGuidelines/Pradhan%20Mantri%20UJJWALA%20Yojna%20Guideline.pdf",
    "https://cag.gov.in/uploads/download_audit_report/2022/Chapter-VI---Pre-and-Post-Matric-Scholarship-schemes-for-Minority-Students-0668f9da698eeb5.96162872.pdf",
    "https://handlooms.nic.in/weaver_mudra%20_scheme.php",
    "https://hisar.gov.in/district-social-welfare-office-hisar/https://hisar.gov.in/district-social-welfare-office-hisar/",
    "https://ladlibahinstorage.s3.ap-south-1.amazonaws.com/site-pdf/%E0%A4%AE%E0%A4%BE%E0%A4%B0%E0%A5%8D%E0%A4%97%E0%A4%A6%E0%A4%B0%E0%A5%8D%E0%A4%B6%E0%A4%95+%E0%A4%B8%E0%A5%82%E0%A4%9A%E0%A4%A8%E0%A4%BE+%E0%A4%A6%E0%A4%BF.%E0%A5%A8%E0%A5%AD.%E0%A5%A6%E0%A5%AD.%E0%A5%A8%E0%A5%AA.pdf#toolbar=0",
    "https://msme.gov.in/sites/default/files/Revisedguidelines07.12.2023.pdf",
    "https://msme.gov.in/sites/default/files/final-guidlines-for-2nd-loan.pdf",
    "https://north24parganas.gov.in/sites/default/files/training_ppt_bsk.pdf",
    "https://nrega.nic.in/Circular_Archive/archive/Operational_guidelines_4thEdition_eng_2013.pdf",
    "https://nrega.nic.in/Circular_Archive/archive/nrega_doc_FAQs.pdf",
    "https://pune.gov.in/scheme/indira-gandhi-national-disability-pension-scheme/",
    "https://pune.gov.in/scheme/indira-gandhi-national-old-age-pension-scheme/",
    "https://saara.mp.gov.in/saaraweb/BhuSwamiAdhikar/ruralplot.html",
    "https://schemes.rajasthan.gov.in/scheme/detail/111",
    "https://schemes.rajasthan.gov.in/scheme/detail/112",
    "https://schemes.rajasthan.gov.in/scheme/detail/113",
    "https://schemes.rajasthan.gov.in/scheme/detail/128",
    "https://scholarships.gov.in/public/FAQ/renewalstudentfaqs.pdf",
    "https://scholarships.gov.in/registrations/#/",
    "https://sjsa.maharashtra.gov.in/en/ramai-awas-gharkul-scheme-sc-nav-buddha-urban-and-rural",
    "https://sjsa.maharashtra.gov.in/en/scheme-category/education-training",
    "https://sjsa.maharashtra.gov.in/en/scheme-category/education-training?&Submit=Submit&page=1",
    "https://sjsa.maharashtra.gov.in/mr/schemes-page?scheme_nature=37",
    "https://sjsa.maharashtra.gov.in/sites/default/files/vjntscheme/eng/2-01.pdf",
    "https://sjsa.maharashtra.gov.in/sites/default/files/vjntscheme/eng/2-14.pdf",
    "https://telanganaepass.cgg.gov.in/KalyanaLakshmiLinks.do",
    "https://tnlegalservices.tn.gov.in/swwe/Annexure_English.pdf",
    "https://tribal.gov.in/downloads/Livelihood/Guidelines/PMJVMGuidelines.pdf",
    "https://www.education.gov.in/sites/upload_files/mhrd/files/document-reports/PM_Vidyalaxmi_Scheme_Guidelines.pdf",
    "https://www.education.gov.in/sites/upload_files/mhrd/files/upload_document/CSIS%20-%20NewGuidelines.pdf",
    "https://www.education.gov.in/sites/upload_files/mhrd/files/upload_document/IBAM.pdf",
    "https://www.education.gov.in/sites/upload_files/mhrd/files/upload_document/pmusp_csis.pdf",
    "https://www.mha.gov.in/sites/default/files/2022-08/PMSS-GLiens081008%5B1%5D.pdf",
    "https://www.mha.gov.in/sites/default/files/2022-08/Swatantrata_sainik_27102016%5B1%5D.PDF",
    "https://www.mha.gov.in/sites/default/files/2022-09/Annexure%25208%5B1%5D.pdf",
)


def url_key(url):
    return (url or "").split("#", 1)[0].rstrip("/")


DEAD_KEYS = {url_key(url) for url in DEAD_REFERENCE_URLS}


def is_dead_reference(url):
    return url_key(url) in DEAD_KEYS


def _replace_dead_text(text, source):
    if not isinstance(text, str) or "http" not in text:
        return text
    for url in sorted(DEAD_REFERENCE_URLS, key=len, reverse=True):
        if url in text:
            text = text.replace(url, source)
    for key in sorted(DEAD_KEYS, key=len, reverse=True):
        if key and key in text:
            text = text.replace(key, source)
    return text


def _replace_dead_tree(value, source):
    if isinstance(value, str):
        return _replace_dead_text(value, source)
    if isinstance(value, list):
        return [_replace_dead_tree(item, source) for item in value]
    if isinstance(value, dict):
        return {key: _replace_dead_tree(item, source) for key, item in value.items()}
    return value


def prune_links(scheme):
    """Drop confirmed-404 references and point a dead apply link at myScheme."""
    source = scheme.get("sourceUrl") or ""
    slug = scheme.get("slug") or ""
    references = []
    for item in scheme.get("references") or []:
        url = (item or {}).get("url") or ""
        if is_dead_reference(url) or url == source:
            continue
        if slug == "cmkvy" and "cgwcd.gov.in" in url:
            continue
        references.append(item)
    scheme["references"] = references

    apply_links = []
    seen = set()
    for item in scheme.get("applyLinks") or []:
        url = (item or {}).get("url") or ""
        mode = (item or {}).get("mode") or ""
        if is_dead_reference(url) or (slug == "cmkvy" and ("cgwcd.gov.in" in url or url == source)):
            url = source
            mode = "myScheme"
        if not url or url in seen:
            continue
        seen.add(url)
        link = dict(item)
        link["url"] = url
        if mode:
            link["mode"] = mode
        apply_links.append(link)
    scheme["applyLinks"] = apply_links
    return _replace_dead_tree(scheme, source)


def fix_scheme_links(scheme):
    slug = scheme.get("slug") or ""
    fixed = _walk(scheme, slug)
    fixed["slug"] = slug
    return prune_links(fixed)
