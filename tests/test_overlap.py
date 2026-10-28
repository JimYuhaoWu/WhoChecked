"""
tests/test_overlap.py
---------------------
Pins the author-overlap derivation. Names here are invented placeholders.

    python -m unittest discover tests
"""

import unittest

from whochecked.overlap import classify_overlap, norm_author


class NormAuthor(unittest.TestCase):

    def test_accent_and_case_fold(self):
        self.assertEqual(norm_author("Zoë Ångström"), norm_author("zoe angstrom"))

    def test_two_letter_surname_survives(self):
        # CFCR once collapsed every two-letter surname to `anon` under a
        # longest-token rule.
        self.assertEqual(norm_author("Tam Xu"), "xu|t")

    def test_initials_with_dots_and_hyphens(self):
        self.assertEqual(norm_author("T.-K. Xu"), "xu|t")

    def test_empty(self):
        self.assertEqual(norm_author(""), "")
        self.assertEqual(norm_author(" . "), "")

    @unittest.expectedFailure
    def test_surname_first_matches_given_name_first(self):
        # Known defect, ROADMAP M2: Europe PMC writes "Xu T" where Crossref
        # writes "Tam Xu", and the last token is taken as the surname.
        self.assertEqual(norm_author("Xu T"), norm_author("Tam Xu"))


class ClassifyOverlap(unittest.TestCase):

    P = {"xu|t", "osei|k", "brandt|m"}

    def test_no_shared_authors_is_independent(self):
        self.assertEqual(classify_overlap(self.P, {"lund|a", "okafor|c"}),
                         ("independent", set()))

    def test_empty_evaluating_authors_is_unknown(self):
        self.assertEqual(classify_overlap(self.P, set())[0], "unknown")

    def test_empty_primary_authors_is_unknown(self):
        self.assertEqual(classify_overlap(set(), {"lund|a"})[0], "unknown")

    def test_empty_names_are_not_shared_authors(self):
        kind, shared = classify_overlap(self.P | {""}, {"", "lund|a"})
        self.assertEqual((kind, shared), ("independent", set()))

    def test_list_of_only_empty_names_is_unknown(self):
        self.assertEqual(classify_overlap(self.P, {""})[0], "unknown")
        self.assertEqual(classify_overlap({""}, {"lund|a"})[0], "unknown")

    def test_empty_names_do_not_count_toward_the_fraction(self):
        # 1 shared of 2 real evaluating authors, not 1 of 3.
        self.assertEqual(classify_overlap(self.P, {"xu|t", "lund|a", ""})[0],
                         "same-group")

    def test_minority_shared_is_partial(self):
        kind, shared = classify_overlap(self.P, {"xu|t", "lund|a", "okafor|c"})
        self.assertEqual((kind, shared), ("partial", {"xu|t"}))

    def test_exactly_half_shared_is_same_group(self):
        self.assertEqual(classify_overlap(self.P, {"xu|t", "lund|a"})[0],
                         "same-group")

    def test_fraction_is_of_evaluating_authors_not_primary(self):
        # 1 of 3 primary authors, but 1 of 1 evaluating author.
        self.assertEqual(classify_overlap(self.P, {"osei|k"})[0], "same-group")


if __name__ == "__main__":
    unittest.main()
