"""
tests/test_github.py
--------------------
Reading a repository's licence, offline: GitHub is never called, and every
repository is invented.

    python -m unittest discover tests
"""

import unittest
from unittest import mock

import requests

from whochecked import github


class Parse(unittest.TestCase):

    def test_links_give_owner_and_name(self):
        for text in ("https://github.com/some-owner/a.repo",
                     "http://www.github.com/some-owner/a.repo",
                     "github.com/some-owner/a.repo",
                     "https://github.com/some-owner/a.repo/",
                     "https://github.com/some-owner/a.repo.git",
                     "https://GitHub.com/some-owner/a.repo/tree/main/src",
                     "https://github.com/some-owner/a.repo?tab=readme#top"):
            self.assertEqual(github.parse_repo(text), "some-owner/a.repo", text)

    def test_anything_else_is_refused(self):
        for text in ("", "some-owner/a.repo", "https://gitlab.com/o/r",
                     "https://github.com/o", "https://github.com/",
                     "https://github.com.example.org/o/r",
                     "https://example.org/github.com/o/r",
                     "https://github.com/o/..", "https://github.com/../r",
                     "https://github.com/o/r r", "https://github.com/o%2F/r",
                     "https://github.com/" + "o" * 40 + "/r"):
            self.assertIsNone(github.parse_repo(text), text)


def reply(status=200, body=None):
    return mock.Mock(status_code=status, json=mock.Mock(return_value=body))


class Licence(unittest.TestCase):

    def ask(self, **kw):
        with mock.patch.object(github.requests, "get", **kw) as g:
            answer = github.licence("some-owner/a-repo")
        return answer, g

    def test_a_named_licence(self):
        a, g = self.ask(return_value=reply(body={
            "html_url": "https://github.com/some-owner/renamed",
            "license": {"spdx_id": "MIT", "name": "MIT License"}}))
        self.assertEqual((a["state"], a["spdx"], a["name"]),
                         ("licence", "MIT", "MIT License"))
        self.assertEqual(a["url"], "https://github.com/some-owner/renamed")
        self.assertRegex(a["checked"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(g.call_args.args[0],
                         "https://api.github.com/repos/some-owner/a-repo")

    def test_a_licence_file_it_cannot_identify(self):
        a, _ = self.ask(return_value=reply(body={
            "license": {"spdx_id": "NOASSERTION", "name": "Other"}}))
        self.assertEqual(a["state"], "unidentified")
        self.assertNotIn("spdx", a)

    def test_no_licence_detected(self):
        a, _ = self.ask(return_value=reply(body={"license": None}))
        self.assertEqual(a["state"], "none")

    def test_not_found_or_private(self):
        a, _ = self.ask(return_value=reply(404))
        self.assertEqual(a["state"], "not_found")

    def test_a_refusal_or_a_failure_is_no_answer(self):
        for kw in ({"return_value": reply(403)}, {"return_value": reply(429)},
                   {"return_value": reply(500)},
                   {"side_effect": requests.ConnectionError("x")},
                   {"side_effect": requests.Timeout("x")}):
            self.assertEqual(self.ask(**kw)[0]["state"], "no_answer", kw)

    def test_a_reply_that_is_not_json_is_no_answer(self):
        bad = mock.Mock(status_code=200, json=mock.Mock(side_effect=ValueError))
        self.assertEqual(self.ask(return_value=bad)[0]["state"], "no_answer")


if __name__ == "__main__":
    unittest.main()
