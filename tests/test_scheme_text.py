import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from scheme_text import age_bounds, benefit_amount, farmer_quote, income_ceiling, male_must_be_sc_st
from eligibility_rules import annotate_scheme
from link_fixes import fix_scheme_links, fix_url_string


class SchemeTextTests(unittest.TestCase):
    def test_pm_kisan_benefit_line_is_kept_verbatim(self):
        text = (
            "  - **Financial Assistance:** An amount of ₹6,000/- per year in 3 equal "
            "installments of ₹2,000/- every four months is provided to each eligible family.\n"
        )
        self.assertIn("₹6,000", benefit_amount(text))
        self.assertIn("₹2,000", benefit_amount(text))

    def test_multiple_amount_lines_stay_blank(self):
        text = "1. On Death- the Nominee shall get Rs. 2 Lakhs.\n1. Subscriber shall get Rs. 1 Lakh.\n"
        self.assertEqual(benefit_amount(text), "")

    def test_income_ceiling_from_official_sentence(self):
        text = (
            "The scholarship award will be sanctioned in the case of students whose "
            "parents/guardians' income from all sources does not exceed ₹ 2,50,000/- per annum."
        )
        amount, note = income_ceiling(text)
        self.assertEqual(amount, 250000)
        self.assertIn("2,50,000", note)

    def test_loan_amount_is_not_an_income_ceiling(self):
        text = "Facilitation of composite loan between ₹10 Lakhs and ₹100 Lakhs."
        amount, note = income_ceiling(text)
        self.assertIsNone(amount)
        self.assertEqual(note, "")

    def test_male_sc_st_quote(self):
        text = "If the applicant is a male, he must be from SC / ST category."
        self.assertIn("SC / ST", male_must_be_sc_st(text))

    def test_multiple_income_bands_are_not_collapsed(self):
        text = (
            "a) Economically Weaker Section (EWS): households with annual income up to ₹3,00,000.\n"
            "b) Low Income Group (LIG): households with annual income between ₹3,00,001 and ₹6,00,000."
        )
        amount, note = income_ceiling(text)
        self.assertIsNone(amount)
        self.assertEqual(note, "")

    def test_conditional_apl_ceiling_is_left_blank(self):
        text = "The applicant's family annual income should not exceed ₹8,00,000/- if from the APL (Above Poverty Line) category."
        amount, _note = income_ceiling(text)
        self.assertIsNone(amount)

    def test_disability_requirement_is_quoted(self):
        from scheme_text import disability_required_quote, enrich_criteria
        text = "1. Disabled due to leprosy (with any percentage of disability)."
        self.assertIn("leprosy", disability_required_quote(text))
        criteria = enrich_criteria({"occupations": ["All"], "disability": "No"}, text)
        self.assertEqual(criteria["disability"], "Yes")

    def test_farmer_sentence_is_quoted(self):
        text = "1. The applicant must be a farmer.\n1. The applicant must be a resident of Telangana."
        self.assertIn("must be a farmer", farmer_quote(text))

    def test_double_encoded_entities_are_cleaned(self):
        from scheme_text import clean_text
        self.assertEqual(clean_text("Agriculture &amp; Allied"), "Agriculture & Allied")

    def test_not_be_more_than_is_an_income_ceiling(self):
        text = "The family income from all sources should not be more than ₹8,00,000 per annum during the financial year."
        amount, note = income_ceiling(text)
        self.assertEqual(amount, 800000)
        self.assertIn("8,00,000", note)

    def test_scholarship_name_is_student_only_and_swanath_is_an_orphan_scheme(self):
        scheme = annotate_scheme({
            "slug": "aicte-ssss",
            "name": {"en": "AICTE-Swanath Scholarship Scheme For Students"},
            "eligibility": {"en": "1. The candidate should be one of the following: (i) an orphan, OR (ii) whose either or both parents died due to Covid 19. The family income from all sources should not be more than ₹8,00,000 per annum."},
            "criteria": {"occupations": [], "disability": "No", "studentOnly": False, "ageMax": None, "bplOnly": False},
        })
        self.assertTrue(scheme["criteria"]["studentOnly"])
        self.assertIn("orphan", scheme["criteria"]["specialGroups"])
        self.assertEqual(scheme["criteria"]["incomeCeilingInr"], 800000)

    def test_pmuy_close_date_stays_and_points_at_ujjwala_2(self):
        scheme = annotate_scheme({
            "slug": "pmuy",
            "name": {"en": "Pradhan Mantri Ujjwala Yojana"},
            "closeDate": "2021-09-30",
            "eligibility": {"en": "An adult woman belonging to a poor household will be eligible under UJJWALA 2.0."},
            "criteria": {},
        })
        self.assertEqual(scheme["closeDate"], "2021-09-30")
        self.assertIn("Ujjwala 2.0", scheme["closeDateNote"])

    def test_bad_apply_links_are_replaced(self):
        self.assertEqual(
            fix_url_string("https://pmkisan.gov.in/RegistrationFormnew.aspx", "pm-kisan"),
            "https://pmkisan.gov.in/RegistrationFormupdated.aspx",
        )
        self.assertEqual(
            fix_url_string("http://www.scholarships.gov.in/", "sak-deg"),
            "https://scholarships.gov.in/",
        )
        self.assertNotIn("translate.goog", fix_url_string("https://serviceonline-bihar-gov-in.translate.goog/path", "mkvy"))
        self.assertIn("serviceonline.bihar.gov.in", fix_url_string("https://serviceonline-bihar-gov-in.translate.goog/path", "mkvy"))
        self.assertNotIn("164.100", fix_url_string("https://164.100.158.73/registration.htm", "affdf-serious-disease-treatment"))
        self.assertNotIn("pmkvyofficial.org", fix_url_string("https://www.pmkvyofficial.org/trainingcenter", "pmkvy-stt"))
        self.assertNotIn("cscindia.info", fix_url_string("https://cscindia.info/", "pmay-u"))
        scheme = fix_scheme_links({
            "slug": "cmkvy",
            "sourceUrl": "https://www.myscheme.gov.in/schemes/cmkvy",
            "applyLinks": [{"mode": "Offline", "url": "https://cgwcd.gov.in/kanya-vivah"}],
            "references": [
                {"title": "Guidelines", "url": "https://cgwcd.gov.in/guidelines"},
                {"title": "FAQ", "url": "https://scholarships.gov.in/registrations/#/"},
            ],
            "howToApply": {
                "en": "Read https://nrega.nic.in/Circular_Archive/archive/nrega_doc_FAQs.pdf before you apply.",
            },
        })
        self.assertEqual(scheme["applyLinks"], [{
            "mode": "myScheme",
            "url": "https://www.myscheme.gov.in/schemes/cmkvy",
        }])
        self.assertEqual(scheme["references"], [])
        self.assertNotIn("nrega.nic.in", scheme["howToApply"]["en"])
        self.assertIn("myscheme.gov.in/schemes/cmkvy", scheme["howToApply"]["en"])

    def test_a_death_benefit_sentence_is_not_treated_as_settled(self):
        scheme = annotate_scheme({
            "slug": "fseg",
            "name": {"en": "Farmer Suicide Ex-Gratia"},
            "brief": {"en": ""},
            "eligibility": {
                "en": "1. The deceased farmer should have been a resident of Andhra Pradesh.\n"
                "1. The beneficiary should be a family member of the deceased farmer."
            },
            "criteria": {"occupations": ["Farmer"]},
        })
        codes = [item["code"] for item in scheme["criteria"]["uncertain"]]
        self.assertIn("unmapped", codes)

    def test_apy_income_tax_line_from_the_brief_stays_open(self):
        scheme = annotate_scheme({
            "slug": "apy",
            "name": {"en": "Atal Pension Yojana"},
            "brief": {"en": "A savings account holder aged 18-40 years, who is not an income tax-payee."},
            "eligibility": {"en": "1. The minimum age of joining APY is 18 years and maximum is 40 years."},
            "criteria": {"ageMin": 18, "ageMax": 40},
        })
        quotes = " ".join(item["quote"] for item in scheme["criteria"]["uncertain"])
        self.assertIn("income tax", quotes)

    def test_blank_age_facet_takes_the_stated_window(self):
        scheme = annotate_scheme({
            "slug": "ignwpsmp",
            "name": {"en": "Indira Gandhi National Widow Pension Scheme-Madhya Pradesh"},
            "brief": {"en": ""},
            "eligibility": {
                "en": "1. The applicant should be a domicile of the state of Madhya Pradesh.\n"
                "1. The applicant should be from a Below Poverty Line (BPL) family.\n"
                "1. The application should be aged between 40 to 79 years."
            },
            "criteria": {"ageMin": None, "ageMax": None, "genders": ["Female"], "bplOnly": True},
        })
        self.assertEqual(scheme["criteria"]["ageMin"], 40)
        self.assertEqual(scheme["criteria"]["ageMax"], 79)
        self.assertEqual(scheme["criteria"]["uncertain"], [])

    def test_minimum_age_sentence_fills_a_blank_minimum(self):
        scheme = annotate_scheme({
            "slug": "wpup",
            "name": {"en": "Widow Pension - Uttar Pradesh"},
            "brief": {"en": ""},
            "eligibility": {
                "en": "1. The applicant should be a permanent resident of Uttar Pradesh state.\n"
                "1. The applicant's husband has died.\n"
                "1. The age of the applicant should not be less than 18 years.\n"
                "1. The annual income of the applicant and her family from all sources should not exceed ₹ 2,00,000/-"
            },
            "criteria": {"ageMin": None, "ageMax": None, "genders": ["Female"]},
        })
        self.assertEqual(scheme["criteria"]["ageMin"], 18)
        self.assertIsNone(scheme["criteria"]["ageMax"])
        self.assertEqual(scheme["criteria"]["uncertain"], [])

    def test_age_and_rural_sentences_are_settled_by_the_form(self):
        scheme = annotate_scheme({
            "slug": "mgnrega",
            "name": {"en": "Mahatma Gandhi National Rural Employment Guarantee Act"},
            "brief": {"en": ""},
            "eligibility": {
                "en": "1. The applicant must be at least 18 years of age.\n"
                "1. The applicant must be residing in a Rural Area."
            },
            "criteria": {},
        })
        self.assertEqual(scheme["criteria"]["uncertain"], [])

    def test_age_window_and_open_ends(self):
        tested = [0, 18, 40, 60, 100]
        self.assertEqual(age_bounds([18, 40, 60], tested), (18, 60))
        self.assertEqual(age_bounds([0, 18, 40, 60, 100], tested), (None, None))
        self.assertEqual(age_bounds([60, 100], tested), (60, None))
        self.assertEqual(age_bounds([18, 60], tested), (None, None))


if __name__ == "__main__":
    unittest.main()
