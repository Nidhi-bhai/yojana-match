# YojanaMatch

YojanaMatch is a free static site that asks eight questions and lists central and state government schemes a person may qualify for. Each scheme shows the benefit when the official page states one amount, the eligibility text, documents, the official apply link when myScheme lists one, and the source URL.

It is not a government website. Confirm every scheme on the official portal before applying.

## Questions

State, age, gender, annual family income band, occupation (farmer, student, MSME / self-employed, woman entrepreneur, salaried, unemployed, or other), category (General, OBC, SC, ST, PVTG, DNT), disability, and rural or urban.

The interface is in English, Hindi, and Telugu. Scheme text is the official myScheme copy in those languages when the portal provides it.

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

Facets come from myScheme search filters. Values inside one facet are alternatives. A facet that is missing or `All` / `Both` does not exclude anyone.

- State schemes are limited to the states on the record. Central schemes tagged `All` are shown in every state.
- Disability-only and student-only schemes come from the official yes/no tags.
- Age bounds come from the official age filter, sampled at fixed ages. A gap in the middle turns the age filter off for that scheme.
- If a scheme is tagged for a specific occupation such as Farmer, that tag is used even when the employment tag says Employed. That is why PM-KISAN still matches farmers.
- If the eligibility text says a male applicant must be from SC/ST, that sentence is stored and applied. Women are not limited to those categories by that sentence.
- If the occupation facet is empty and the eligibility text says the applicant must be a farmer, the scheme is treated as farmer-only.
- If the eligibility text says the applicant is disabled due to a stated cause, the scheme is treated as disability-only and the sentence is kept.
- Below-poverty-line schemes are shown for the lowest income band, with a note to confirm that status.
- Land ownership, pregnancy, and other conditions that are only in the prose are shown on the page. They are not guessed.

## Five checked profiles

These are asserted in `tests/profiles.json` by `node --test tests/match.test.js`.

1. **Rural Uttar Pradesh farmer.** Man, 40, general category, income under ₹1 lakh, no disability. Matches PM-KISAN, PM Fasal Bima Yojana, Kisan Credit Card, and Pradhan Mantri Suraksha Bima Yojana. Does not match the ST post-matric scholarship, Matru Vandana, Stand-Up India, the ICAR SC/ST scholarship, Tamil Nadu’s disability pension, or UP divyang pension.
2. **Urban Bihar SC student.** Woman, 18, income under ₹1 lakh, no disability. Matches the ICAR post-matric scholarship for SC/ST students. Does not match PM-KISAN, Kisan Credit Card, Matru Vandana, Stand-Up India, the ST-only post-matric scholarship, a Gujarat SC scholarship, or Karnataka’s Nekar Samman Yojana. The ICAR page still requires admission in an agricultural university.
3. **Urban Maharashtra woman entrepreneur.** Woman, 32, general category, income ₹2.5–5 lakh, no disability. Matches Stand-Up India and PMSBY. Does not match PM-KISAN, Kisan Credit Card, the ST scholarship, rural-only crop insurance, a Gujarat men-only scheme, or Ujjwala (marked below poverty line).
4. **Rural Karnataka senior with a disability.** Man, 67, OBC, unemployed, income under ₹1 lakh. Matches PMSBY and the Indira Gandhi National Disability Pension Scheme. Does not match PM-KISAN, Stand-Up India, the student scholarships, or Matru Vandana. The pension text also requires disability above 80 percent, and the lowest income band is only a proxy for the below-poverty-line tag.
5. **Rural Telangana ST farmer.** Woman, 29, income ₹1–2.5 lakh, no disability. Matches PM-KISAN, PM Fasal Bima, Kisan Credit Card, Stand-Up India, and Rythu Bima. Does not match the student scholarships, Tamil Nadu disability pension, or UP pre-matric scholarship. Rythu Bima still requires a Telangana land record.

## Pages and search

Each scheme has a page titled “eligibility, benefits, how to apply”, plus category and state pages, `sitemap.xml`, and `robots.txt`. The site is the `docs/` folder, meant for GitHub Pages from the `main` branch (`/docs`).

Live URL, once Pages is enabled: <https://nidhi-bhai.github.io/yojana-match/>

## Payments and ads

`docs/config.js` sets `PAYPAL_CLIENT_ID`. Replace `YOUR_PAYPAL_CLIENT_ID` with the public PayPal client id. The $2 “Application help pack” is a PDF checklist of the schemes in the result, created after PayPal Smart Buttons capture the payment. No payment runs while the placeholder is in place.

The results page and each scheme page include an AdSense placeholder. It does not contain a publisher id.

## Footer

Built by [Nidhi Karuturi](https://github.com/Nidhi-bhai).

## Tests

```bash
python3 -m unittest tests/test_scheme_text.py
node --test tests/match.test.js
python3 scripts/build_site.py
```
