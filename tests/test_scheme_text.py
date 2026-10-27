import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from scheme_text import age_bounds, benefit_amount, farmer_quote, income_ceiling, male_must_be_sc_st


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

    def test_age_window_and_open_ends(self):
        tested = [0, 18, 40, 60, 100]
        self.assertEqual(age_bounds([18, 40, 60], tested), (18, 60))
        self.assertEqual(age_bounds([0, 18, 40, 60, 100], tested), (None, None))
        self.assertEqual(age_bounds([60, 100], tested), (60, None))
        self.assertEqual(age_bounds([18, 60], tested), (None, None))


if __name__ == "__main__":
    unittest.main()
