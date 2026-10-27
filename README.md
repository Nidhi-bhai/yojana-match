# YojanaMatch

YojanaMatch is a free static site that asks about state, age, income, work, and a few eligibility conditions, then lists central and state government schemes a person may qualify for. Each scheme shows the benefit when the official page states one amount, the eligibility text, documents, the official apply link when myScheme lists one, and the source URL.

It is not a government website. Confirm every scheme on the official portal before applying.

## Questions

State, age, gender, annual family income band, occupation (farmer, student, MSME / self-employed, woman entrepreneur, salaried, unemployed, or other), category (General, OBC, SC, ST, PVTG, DNT), disability, and rural or urban. Two further answers are optional groups (ex-serviceman, freedom fighter, orphan, widow, police or CAPF ward) and whether the household is on a ration-card, SECC, or below-poverty-line list. States with no state scheme in the catalog stay in the dropdown and are labelled “central schemes only”.

The interface is in English, Hindi, and Telugu. English and Hindi scheme text is the myScheme copy. Telugu is a machine translation, marked beta on the site, and should be checked against the English.

## Where the data comes from

Records are copied from [myScheme](https://www.myscheme.gov.in/), the official Government of India scheme portal. `data/schemes.json` is the catalog. Every scheme has:

- `sourceUrl` on myscheme.gov.in
- `lastVerified` (`2026-10-27` for this seed)
- benefit text, and `benefitAmount` only when the official benefits text has a single amount line
- an income ceiling only when the eligibility text states one annual limit

Blank means the official page did not state that fact. Amounts are not estimated.

The browser copy in `docs/data/schemes.json` omits the long “how to apply” text. That text is on each scheme page.

To refresh the catalog, set `MY_SCHEME_API_KEY` to a myScheme read key and run `python3 scripts/fetch_schemes.py`, then `python3 scripts/build_site.py`. The key is not stored in the repo.

## How matching works

A scheme is a confirmed match only when every structured rule fits. Anything the form cannot settle is listed under “Possibly eligible, check conditions”. That section is not a match and it is not put in the PDF.

- State schemes are limited to the states on the record. Central schemes tagged `All` are shown in every state.
- Names containing scholarship, student, pre-matric, or post-matric are student-only.
- Optional questions cover ex-servicemen, freedom fighters, orphans (including a Covid-19 death or a martyr’s ward), widows, and wards of police or Central Armed Police Forces. Those schemes stay hidden until the person opts in.
- Ration card, family card, SECC, and below-poverty-line schemes follow the yes / no / not sure answer. “Not sure”, and a yes that still leaves a deprivation list, stay in the check section.
- An income ceiling is stored only when the eligibility text states one. A band that sits entirely above the ceiling is excluded. A band that crosses it is a check, not a match.
- A myScheme close date before 2026-10-27 removes the scheme from matches and from the PDF. The page shows a closed badge. Stand-Up India (2025-03-31), Mukhyamantri Aawasiye Bhu-Adhikaar Yojana (2023-05-31), and the 2021 Ujjwala record are closed. The 2021 record’s text describes Ujjwala 2.0, which is the separate open record.
- If the official text still states land, a bank account, a course, rank, pregnancy, or another condition the form does not ask, the scheme is a check. The sentence is kept next to it.
- A scheme with no real restriction, such as Jan Dhan, is a check rather than a match for everyone.

## Five checked profiles

These are asserted in `tests/profiles.json` by `node --test tests/match.test.js`. The same file also sweeps 5,040 profiles and fails if any scheme is a confirmed match for 80 percent or more of them.

1. **Rural Uttar Pradesh farmer.** Man, 40, general category, income under ₹1 lakh, no disability. Confirmed matches include Atal Pension Yojana, MGNREGA, and Per Drop More Crop. PM-KISAN, Fasal Bima, Kisan Credit Card, and PMSBY are checks because of land or a bank account. Scholarships, the freedom-fighter pension, and closed Stand-Up India are excluded.
2. **Urban Bihar SC student.** Woman, 18, income under ₹1 lakh. The ICAR scholarship and INSPIRE are checks, not confirmed matches. Farmer schemes, Swanath, and Nekar Samman are excluded.
3. **Urban Maharashtra woman entrepreneur.** Woman, 32, general category, income ₹2.5–5 lakh. Stand-Up India is closed and excluded. PMSBY, Matru Vandana, and PM-JAY are checks. The 2021 Ujjwala record is closed.
4. **Rural Karnataka senior with a disability.** Man, 67, OBC, unemployed, income under ₹1 lakh, and he says he is on a below-poverty-line list. MGNREGA matches. The Indira Gandhi disability pension stays a check because the page states a disability percentage. Nekar Samman stays a check because it is for weavers.
5. **Rural Telangana ST farmer.** Woman, 29, income ₹1–2.5 lakh. The Telangana ₹5 lakh farmer insurance matches. PM-KISAN, Fasal Bima, Kisan Credit Card, and Rythu Bima are checks because of land records. Stand-Up India is closed.

## Pages and search

Each scheme has a page titled “eligibility, benefits, how to apply”, plus category and state pages, `sitemap.xml`, and `robots.txt`. The site is the `docs/` folder, meant for GitHub Pages from the `main` branch (`/docs`).

Live URL, once Pages is enabled: <https://nidhi-bhai.github.io/yojana-match/>

## Payments

`docs/config.js` sets `PAYPAL_CLIENT_ID`. The $2 PDF is the same English checklist already shown free on the page. It lists confirmed matches only. After payment, the PayPal order id and the answers are stored in the browser, and “Download again” rebuilds the file. The PDF names nidhi69n@gmail.com for a refund. The ad slot is omitted until a publisher id exists.

`python3 scripts/check_links.py` requests every apply and reference URL. A 404 or 410 fails the run. Timeouts and non-404 HTTP errors are reported as unverified, because many government sites refuse a connection from outside India. `python3 scripts/check_links.py --local` checks the catalog for known 404s and for unofficial domains without making requests. Confirmed 404 references are removed. A dead apply link is pointed at that scheme’s myScheme page.

## Footer

Built by [Nidhi Karuturi](https://github.com/Nidhi-bhai).

## Tests

```bash
python3 -m unittest tests/test_scheme_text.py
node --test tests/match.test.js
python3 scripts/build_site.py
```
