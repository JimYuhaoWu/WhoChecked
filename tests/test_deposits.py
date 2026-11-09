"""
tests/test_deposits.py
----------------------
Reading a deposit's declared licence, offline: Hugging Face and Zenodo are
never called, and every model and record is invented.

    python -m unittest discover tests
"""

import unittest
from unittest import mock

import requests

from whochecked import deposits

MODEL = "huggingface.co/some-owner/a-model"
RECORD = "zenodo.org/records/123"


class Parse(unittest.TestCase):

    def test_hugging_face_links(self):
        for text in ("https://huggingface.co/some-owner/a-model",
                     "huggingface.co/some-owner/a-model",
                     "https://www.huggingface.co/some-owner/a-model/",
                     "https://huggingface.co/some-owner/a-model/tree/main",
                     "https://HuggingFace.co/some-owner/a-model?x=1#top"):
            self.assertEqual(deposits.parse_link(text), MODEL, text)

    def test_zenodo_links_and_dois(self):
        for text in ("https://zenodo.org/records/123", "zenodo.org/record/123",
                     "https://zenodo.org/records/123/files/a.h5?download=1",
                     "https://zenodo.org/doi/10.5281/zenodo.123",
                     "https://doi.org/10.5281/zenodo.123",
                     "https://dx.doi.org/10.5281/zenodo.123",
                     "doi:10.5281/zenodo.123", "10.5281/zenodo.123"):
            self.assertEqual(deposits.parse_link(text), RECORD, text)

    def test_anything_else_is_refused(self):
        for text in ("", "some-owner/a-model",
                     "https://huggingface.co/some-owner",
                     "https://huggingface.co/datasets/some-owner/a-set",
                     "https://huggingface.co/spaces/some-owner/an-app",
                     "https://huggingface.co/docs/hub",
                     "https://huggingface.co/../a-model",
                     "https://huggingface.co/some-owner/..",
                     "https://huggingface.co.example.org/o/m",
                     "https://example.org/huggingface.co/o/m",
                     "https://zenodo.org/records/abc",
                     "https://zenodo.org/communities/x",
                     "https://zenodo.org.example.org/records/123",
                     "https://doi.org/10.5061/dryad.123", "10.5281/zenodo."):
            self.assertIsNone(deposits.parse_link(text), text)


def reply(status=200, body=None):
    return mock.Mock(status_code=status, json=mock.Mock(return_value=body))


def ask(link, **kw):
    with mock.patch.object(deposits.requests, "get", **kw) as g:
        return deposits.licence(link), g


class HuggingFace(unittest.TestCase):

    def test_a_declared_licence(self):
        a, g = ask(MODEL, return_value=reply(body={
            "id": "some-owner/a-model", "gated": False,
            "cardData": {"license": "apache-2.0"}}))
        self.assertEqual((a["state"], a["licence"]), ("declared", "apache-2.0"))
        self.assertEqual(a["source"], "Hugging Face model card")
        self.assertNotIn("gated", a)
        self.assertRegex(a["checked"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(g.call_args.args[0],
                         "https://huggingface.co/api/models/some-owner/a-model")

    def test_a_custom_licence_keeps_its_name(self):
        a, _ = ask(MODEL, return_value=reply(body={"cardData": {
            "license": "other", "license_name": "a-community-licence"}}))
        self.assertEqual((a["state"], a["licence"]),
                         ("custom", "a-community-licence"))

    def test_several_licences_read_as_text(self):
        a, _ = ask(MODEL, return_value=reply(body={"cardData": {
            "license": ["mit", "apache-2.0"]}}))
        self.assertEqual(a["licence"], "mit, apache-2.0")

    def test_gated_access_is_reported(self):
        a, _ = ask(MODEL, return_value=reply(body={
            "gated": "manual", "cardData": {"license": "mit"}}))
        self.assertEqual(a["gated"], "manual")

    def test_no_licence_declared(self):
        for body in ({"cardData": {}}, {"cardData": None}, {}):
            self.assertEqual(ask(MODEL, return_value=reply(body=body))[0]["state"],
                             "none", body)

    def test_a_renamed_model_is_shown_under_its_current_name(self):
        a, _ = ask(MODEL, return_value=reply(body={"id": "new-owner/a-model"}))
        self.assertEqual((a["ref"], a["url"]),
                         ("new-owner/a-model", "https://huggingface.co/new-owner/a-model"))

    def test_401_means_not_found(self):
        self.assertEqual(ask(MODEL, return_value=reply(401))[0]["state"], "not_found")


class Zenodo(unittest.TestCase):

    def test_a_declared_licence(self):
        a, g = ask(RECORD, return_value=reply(body={
            "id": 123, "metadata": {"license": {"id": "cc-by-4.0"},
                                    "access_right": "open"}}))
        self.assertEqual((a["state"], a["licence"], a["ref"]),
                         ("declared", "cc-by-4.0", "zenodo.123"))
        self.assertNotIn("access", a)
        self.assertEqual(g.call_args.args[0], "https://zenodo.org/api/records/123")

    def test_a_concept_id_is_shown_as_the_latest_version(self):
        a, _ = ask(RECORD, return_value=reply(body={"id": 124, "metadata": {}}))
        self.assertEqual((a["ref"], a["url"]),
                         ("zenodo.124", "https://zenodo.org/records/124"))

    def test_no_licence_declared(self):
        a, _ = ask(RECORD, return_value=reply(body={
            "metadata": {"license": None, "access_right": "open"}}))
        self.assertEqual(a["state"], "none")

    def test_restricted_and_embargoed_access_are_reported(self):
        a, _ = ask(RECORD, return_value=reply(body={"metadata": {
            "access_right": "embargoed", "embargo_date": "2027-04-01"}}))
        self.assertEqual((a["access"], a["embargo"]), ("embargoed", "2027-04-01"))

    def test_not_found(self):
        for status in (404, 410):
            self.assertEqual(ask(RECORD, return_value=reply(status))[0]["state"],
                             "not_found")


class Failure(unittest.TestCase):

    def test_a_refusal_or_a_failure_is_no_answer(self):
        for link in (MODEL, RECORD):
            for kw in ({"return_value": reply(403)}, {"return_value": reply(429)},
                       {"return_value": reply(500)},
                       {"side_effect": requests.ConnectionError("x")},
                       {"side_effect": requests.Timeout("x")}):
                self.assertEqual(ask(link, **kw)[0]["state"], "no_answer", (link, kw))

    def test_a_reply_that_is_not_json_is_no_answer(self):
        bad = mock.Mock(status_code=200, json=mock.Mock(side_effect=ValueError))
        for link in (MODEL, RECORD):
            self.assertEqual(ask(link, return_value=bad)[0]["state"], "no_answer")


if __name__ == "__main__":
    unittest.main()
