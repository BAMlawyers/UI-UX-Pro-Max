import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.join(HERE, "..", "server")
sys.path.insert(0, SERVER_DIR)

import liquid_lint  # noqa: E402
import sol  # noqa: E402
from filevine_client import FilevineError  # noqa: E402
from filevine_mcp import Server, handle  # noqa: E402


class SolTests(unittest.TestCase):
    def test_utah_pi_four_years(self):
        r = sol.compute("UT", "2024-03-14", today="2026-10-05")
        d = r["deadlines"][0]
        self.assertEqual(d["deadline"], "2028-03-14")
        self.assertEqual(d["status"], "OK")
        self.assertTrue(d["verify"])

    def test_idaho_gov_notice_is_earliest(self):
        r = sol.compute("ID", "2026-05-02", governmental_entity=True, today="2026-10-05")
        self.assertEqual(r["earliest"]["claim_type"], "gov_notice")
        self.assertEqual(r["earliest"]["deadline"], "2026-10-29")
        self.assertEqual(r["earliest"]["status"], "CRITICAL")

    def test_minor_reports_tolled_but_keeps_untolled(self):
        r = sol.compute("UT", "2023-07-04", client_dob="2014-11-30", today="2026-10-05")
        d = r["deadlines"][0]
        self.assertEqual(d["deadline"], "2027-07-04")
        self.assertEqual(d["minority_tolled_deadline"], "2036-11-30")

    def test_leap_day_rolls_earlier(self):
        self.assertEqual(sol.add_years(sol.parse_date("2024-02-29"), 2).isoformat(), "2026-02-28")

    def test_unsupported_state(self):
        self.assertIn("error", sol.compute("NV", "2025-01-01"))

    def test_expired(self):
        r = sol.compute("AZ", "2020-01-01", today="2026-10-05")
        self.assertEqual(r["deadlines"][0]["status"], "EXPIRED")


class LintTests(unittest.TestCase):
    SCHEMA = {"litigation": ["court", "caseNumber"], "client": []}

    def test_clean_template(self):
        t = ("{{ client.fullname | capitalize }} v. Defendant\n"
             "{% if litigation.caseNumber %}Case No. {{ litigation.caseNumber }}{% endif %}")
        r = liquid_lint.lint(t, schema=self.SCHEMA)
        self.assertTrue(r["ok"], r)

    def test_unknown_field_and_filter(self):
        r = liquid_lint.lint("{{ litigation.judge | Capitalize }}", schema=self.SCHEMA)
        self.assertFalse(r["ok"])
        joined = " ".join(r["errors"])
        self.assertIn("field 'judge'", joined)
        self.assertIn("case-sensitive", joined)

    def test_unclosed_block(self):
        r = liquid_lint.lint("{% if litigation.court %}x")
        self.assertIn("never closed", " ".join(r["errors"]))

    def test_for_loop_vars_are_local(self):
        t = "{% for m in meds %}{{ m.provider }}{% endfor %}"
        r = liquid_lint.lint(t, schema={"meds": ["provider"]})
        self.assertTrue(r["ok"], r)

    def test_split_delimiter(self):
        r = liquid_lint.lint("{ { client.fullname }}")
        self.assertFalse(r["ok"])

    def test_smart_quotes(self):
        r = liquid_lint.lint("{{ litigation.court | default: “TBD” }}")
        self.assertIn("smart quote", " ".join(r["errors"]))


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.s = Server(mock=True)

    def call(self, name, **args):
        resp = handle(self.s, {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                               "params": {"name": name, "arguments": args}})
        return resp["result"]

    def test_search(self):
        r = json.loads(self.call("filevine_search_projects", query="rivera")["content"][0]["text"])
        self.assertEqual(r["results"][0]["projectId"], 10001)

    def test_snapshot_specials(self):
        r = json.loads(self.call("filevine_case_snapshot", project_id=10001)["content"][0]["text"])
        self.assertEqual(r["specials"]["meds"]["billed_total"], 30235.5)
        self.assertEqual(r["sections"]["insurance"]["defendantPolicyLimits"], "1,000,000 CSL")

    def test_writes_blocked_when_disabled(self):
        s = Server(mock=True, allow_writes=False)
        with self.assertRaises(FilevineError):
            s.t_create_note(10001, "x")

    def test_update_section_reports_diff(self):
        r = self.s.t_update_section(10001, "litigation", {"solDate": "2028-03-14"})
        self.assertEqual(r["changed"]["solDate"], {"from": "", "to": "2028-03-14"})

    def test_lint_with_project_type(self):
        r = self.s.t_lint_template("{{ insurance.adjusterName }} {{ insurance.nope }}", project_type_id=501)
        self.assertEqual(len(r["errors"]), 1)

    def test_api_get_rejects_absolute(self):
        res = self.call("filevine_api_get", path="https://evil.example/x")
        self.assertTrue(res["isError"])

    def test_unknown_tool(self):
        resp = handle(self.s, {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                               "params": {"name": "nope"}})
        self.assertIn("error", resp)

    def test_stdio_roundtrip(self):
        msgs = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                        "clientInfo": {"name": "t", "version": "0"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        ]
        proc = subprocess.run(
            [sys.executable, os.path.join(SERVER_DIR, "filevine_mcp.py")],
            input="\n".join(json.dumps(m) for m in msgs) + "\n",
            capture_output=True, text=True, env={**os.environ, "FILEVINE_MOCK": "1"}, timeout=20,
        )
        lines = [json.loads(l) for l in proc.stdout.splitlines() if l.strip()]
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]["result"]["serverInfo"]["name"], "filevine")
        self.assertGreaterEqual(len(lines[1]["result"]["tools"]), 15)


if __name__ == "__main__":
    unittest.main()
