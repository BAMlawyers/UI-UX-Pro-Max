#!/usr/bin/env python3
"""Filevine MCP server (stdio, JSON-RPC 2.0, stdlib only).

Env:
  FILEVINE_PAT, FILEVINE_CLIENT_ID, FILEVINE_CLIENT_SECRET   live credentials
  FILEVINE_USER_ID, FILEVINE_ORG_ID                          optional; resolved from token if unset
  FILEVINE_MOCK=1                                            use bundled fictional data
  FILEVINE_ALLOW_WRITES=1                                    enable note/field writes (off by default)
  FILEVINE_BILLED_FIELD / FILEVINE_PAID_FIELD                collection fields summed for specials
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import liquid_lint  # noqa: E402
import sol  # noqa: E402
from filevine_client import FilevineClient, FilevineError, unwrap_ids  # noqa: E402
from mock_client import MockFilevineClient  # noqa: E402

PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {"name": "filevine", "version": "0.1.0"}


def env_flag(name):
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


class Server:
    def __init__(self, client=None, mock=None, allow_writes=None):
        self.mock = env_flag("FILEVINE_MOCK") if mock is None else mock
        self.client = client or (MockFilevineClient() if self.mock else FilevineClient())
        self.allow_writes = (
            (self.mock or env_flag("FILEVINE_ALLOW_WRITES")) if allow_writes is None else allow_writes
        )
        self.billed_field = os.environ.get("FILEVINE_BILLED_FIELD", "billed")
        self.paid_field = os.environ.get("FILEVINE_PAID_FIELD", "paid")
        self._projects_cache = (0.0, None)

    # -- helpers ----------------------------------------------------------

    def _all_projects(self):
        ts, cached = self._projects_cache
        if cached is not None and time.time() - ts < 300:
            return cached
        items, offset = [], 0
        while True:
            page = self.client.list_projects(limit=1000, offset=offset)
            batch = page.get("items", [])
            items.extend(batch)
            if not page.get("hasMore") or not batch:
                break
            offset += len(batch)
        items = unwrap_ids(items)
        self._projects_cache = (time.time(), items)
        return items

    def _require_writes(self):
        if not self.allow_writes:
            raise FilevineError(
                "Writes are disabled. Set FILEVINE_ALLOW_WRITES=1 to allow Claude to "
                "create notes or update fields in Filevine."
            )

    @staticmethod
    def _num(v):
        if isinstance(v, (int, float)):
            return float(v)
        try:
            return float(str(v).replace("$", "").replace(",", "").strip())
        except ValueError:
            return 0.0

    # -- tools ------------------------------------------------------------

    def t_status(self):
        return {
            "mode": "mock (fictional sample data)" if self.mock else "live",
            "credentials_configured": self.client.configured(),
            "writes_enabled": self.allow_writes,
            "sol_states": sorted(sol.RULES),
        }

    def t_search_projects(self, query="", include_archived=False, limit=25, phase=None):
        q = (query or "").lower().strip()
        out = []
        for p in self._all_projects():
            if p.get("isArchived") and not include_archived:
                continue
            if phase and (p.get("phaseName") or "").lower() != phase.lower():
                continue
            hay = " ".join(str(p.get(k, "")) for k in
                           ("projectName", "clientName", "number", "projectId")).lower()
            if q and q not in hay:
                continue
            out.append({k: p.get(k) for k in (
                "projectId", "projectName", "clientName", "number", "phaseName",
                "projectTypeId", "incidentDate")})
        return {"count": len(out), "results": out[: int(limit)]}

    def t_get_project(self, project_id):
        return unwrap_ids(self.client.get_project(project_id))

    def t_get_section(self, project_id, section):
        return unwrap_ids(self.client.get_form(project_id, section))

    def t_get_collection(self, project_id, section, limit=200):
        return unwrap_ids(self.client.get_collection(project_id, section, limit))

    def t_list_notes(self, project_id, limit=25):
        return unwrap_ids(self.client.list_notes(project_id, limit))

    def t_list_contacts(self, project_id):
        return unwrap_ids(self.client.list_contacts(project_id))

    def t_list_deadlines(self, project_id):
        return unwrap_ids(self.client.list_deadlines(project_id))

    def t_list_documents(self, project_id, limit=200):
        return unwrap_ids(self.client.list_documents(project_id, limit))

    def t_list_sections(self, project_type_id):
        return unwrap_ids(self.client.list_sections(project_type_id))

    def t_get_section_schema(self, project_type_id, section):
        return unwrap_ids(self.client.get_section_schema(project_type_id, section))

    def t_case_snapshot(self, project_id, sections=None, collections=None, notes=10):
        sections = sections or ["intake", "insurance", "litigation"]
        collections = collections or ["meds"]
        snap = {"project": self.t_get_project(project_id), "sections": {},
                "collections": {}, "missing": []}
        for s in sections:
            try:
                snap["sections"][s] = self.t_get_section(project_id, s)
            except FilevineError as e:
                snap["missing"].append(f"section {s}: {e}")
        for c in collections:
            try:
                items = self.t_get_collection(project_id, c).get("items", [])
                rows = [i.get("dataObject", i) for i in items]
                snap["collections"][c] = rows
                if any(self.billed_field in r for r in rows):
                    billed = sum(self._num(r.get(self.billed_field)) for r in rows)
                    paid = sum(self._num(r.get(self.paid_field)) for r in rows)
                    snap.setdefault("specials", {})[c] = {
                        "billed_total": round(billed, 2),
                        "paid_total": round(paid, 2),
                        "providers": len(rows),
                    }
            except FilevineError as e:
                snap["missing"].append(f"collection {c}: {e}")
        for key, fn in (("notes", lambda: self.t_list_notes(project_id, notes)),
                        ("contacts", lambda: self.t_list_contacts(project_id)),
                        ("deadlines", lambda: self.t_list_deadlines(project_id))):
            try:
                snap[key] = fn().get("items", [])
            except FilevineError as e:
                snap["missing"].append(f"{key}: {e}")
        return snap

    def t_sol_check(self, state, incident_date, claim_types=None, governmental_entity=False,
                    client_dob=None, date_of_death=None, as_of=None):
        return sol.compute(state, incident_date, claim_types, governmental_entity,
                           client_dob, date_of_death, today=as_of)

    def t_lint_template(self, template, project_type_id=None, extra_filters=None):
        schema = None
        if project_type_id:
            schema = {}
            for s in self.t_list_sections(project_type_id).get("items", []):
                sel = s.get("sectionSelector")
                detail = self.t_get_section_schema(project_type_id, sel)
                schema[sel] = [f.get("fieldSelector") for f in detail.get("fields", [])]
        return liquid_lint.lint(template, schema=schema, extra_filters=extra_filters)

    def t_create_note(self, project_id, body):
        self._require_writes()
        return unwrap_ids(self.client.create_note(project_id, body))

    def t_update_section(self, project_id, section, fields):
        self._require_writes()
        if not isinstance(fields, dict) or not fields:
            raise FilevineError("fields must be a non-empty object of {fieldSelector: value}.")
        before = self.t_get_section(project_id, section)
        after = unwrap_ids(self.client.update_form(project_id, section, fields))
        return {"changed": {k: {"from": before.get(k), "to": v} for k, v in fields.items()},
                "result": after}

    def t_api_get(self, path, params=None):
        if "://" in path or ".." in path:
            raise FilevineError("path must be a relative API path, e.g. 'Projects/123/Tasks'.")
        return unwrap_ids(self.client.request("GET", path, params=params or {}))


PID = {"type": ["integer", "string"], "description": "Filevine project ID (native)."}
SEC = {"type": "string", "description": "Section selector, e.g. 'intake'. Use filevine_list_sections to discover."}
RO = {"readOnlyHint": True, "openWorldHint": True}

TOOLS = [
    ("filevine_status", "t_status", "Report mode (live/mock), credential status, write permission and supported SOL states.",
     {}, [], RO),
    ("filevine_search_projects", "t_search_projects",
     "Find projects by client name, project name, or case number. Returns project IDs to use with other tools.",
     {"query": {"type": "string"}, "phase": {"type": "string", "description": "Exact phase name filter."},
      "include_archived": {"type": "boolean", "default": False},
      "limit": {"type": "integer", "default": 25}}, [], RO),
    ("filevine_get_project", "t_get_project", "Get a project's core record (name, client, phase, type, incident date).",
     {"project_id": PID}, ["project_id"], RO),
    ("filevine_case_snapshot", "t_case_snapshot",
     "One-call case pull: project, static sections, collections (with billed/paid specials totals), recent notes, contacts, deadlines.",
     {"project_id": PID,
      "sections": {"type": "array", "items": {"type": "string"}, "description": "Default: intake, insurance, litigation."},
      "collections": {"type": "array", "items": {"type": "string"}, "description": "Default: meds."},
      "notes": {"type": "integer", "default": 10}}, ["project_id"], RO),
    ("filevine_get_section", "t_get_section", "Get a static (form) section's field values for a project.",
     {"project_id": PID, "section": SEC}, ["project_id", "section"], RO),
    ("filevine_get_collection", "t_get_collection", "Get a collection section's rows (e.g. medical providers, liens).",
     {"project_id": PID, "section": SEC, "limit": {"type": "integer", "default": 200}},
     ["project_id", "section"], RO),
    ("filevine_list_notes", "t_list_notes", "List recent activity notes on a project.",
     {"project_id": PID, "limit": {"type": "integer", "default": 25}}, ["project_id"], RO),
    ("filevine_list_contacts", "t_list_contacts", "List contacts attached to a project with their roles.",
     {"project_id": PID}, ["project_id"], RO),
    ("filevine_list_deadlines", "t_list_deadlines", "List deadlines calendared on a project.",
     {"project_id": PID}, ["project_id"], RO),
    ("filevine_list_documents", "t_list_documents", "List document metadata (filenames, dates) on a project.",
     {"project_id": PID, "limit": {"type": "integer", "default": 200}}, ["project_id"], RO),
    ("filevine_list_sections", "t_list_sections", "List section selectors for a project type (needed for Liquid tokens).",
     {"project_type_id": {"type": ["integer", "string"]}}, ["project_type_id"], RO),
    ("filevine_get_section_schema", "t_get_section_schema", "List field selectors, names and types in one section of a project type.",
     {"project_type_id": {"type": ["integer", "string"]}, "section": SEC}, ["project_type_id", "section"], RO),
    ("filevine_sol_check", "t_sol_check",
     "Compute conservative SOL / notice-of-claim deadlines (UT, ID, AZ) with citations. Raw dates, no weekend roll; always verify.",
     {"state": {"type": "string", "enum": sorted(sol.RULES)},
      "incident_date": {"type": "string", "description": "YYYY-MM-DD"},
      "claim_types": {"type": "array", "items": {"type": "string", "enum": sol.CLAIM_TYPES},
                      "description": "Default: personal_injury."},
      "governmental_entity": {"type": "boolean", "default": False},
      "client_dob": {"type": "string", "description": "YYYY-MM-DD; enables minority-tolling flag."},
      "date_of_death": {"type": "string"},
      "as_of": {"type": "string", "description": "Override today's date (YYYY-MM-DD)."}},
     ["state", "incident_date"], {"readOnlyHint": True, "openWorldHint": False}),
    ("filevine_lint_template", "t_lint_template",
     "Lint a Filevine document-assembly template (Liquid). With project_type_id, checks every section.field token exists.",
     {"template": {"type": "string"}, "project_type_id": {"type": ["integer", "string"]},
      "extra_filters": {"type": "array", "items": {"type": "string"},
                        "description": "Tenant-specific custom filters to allow."}},
     ["template"], RO),
    ("filevine_create_note", "t_create_note",
     "WRITE: post a note to a project. Show the user the exact note text and get confirmation before calling.",
     {"project_id": PID, "body": {"type": "string"}}, ["project_id", "body"],
     {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True}),
    ("filevine_update_section", "t_update_section",
     "WRITE: update field values in a static section. Show the user a from/to table and get confirmation before calling.",
     {"project_id": PID, "section": SEC,
      "fields": {"type": "object", "description": "{fieldSelector: newValue}"}},
     ["project_id", "section", "fields"],
     {"readOnlyHint": False, "destructiveHint": True, "openWorldHint": True}),
    ("filevine_api_get", "t_api_get",
     "Read-only GET against any Filevine v2 endpoint not wrapped above (relative path, e.g. 'Projects/123/Tasks').",
     {"path": {"type": "string"}, "params": {"type": "object"}}, ["path"], RO),
]
TOOL_INDEX = {t[0]: t for t in TOOLS}


def tool_list():
    return [
        {"name": name, "description": desc,
         "inputSchema": {"type": "object", "properties": props, "required": req},
         "annotations": ann}
        for name, _, desc, props, req, ann in TOOLS
    ]


def handle(server, msg):
    method = msg.get("method")
    mid = msg.get("id")
    if mid is None:  # notification
        return None
    if method == "initialize":
        requested = (msg.get("params") or {}).get("protocolVersion") or PROTOCOL_VERSION
        result = {"protocolVersion": requested, "capabilities": {"tools": {}},
                  "serverInfo": SERVER_INFO}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": tool_list()}
    elif method == "tools/call":
        params = msg.get("params") or {}
        name, args = params.get("name"), params.get("arguments") or {}
        if name not in TOOL_INDEX:
            return {"jsonrpc": "2.0", "id": mid,
                    "error": {"code": -32602, "message": f"Unknown tool: {name}"}}
        try:
            data = getattr(server, TOOL_INDEX[name][1])(**args)
            result = {"content": [{"type": "text", "text": json.dumps(data, indent=2, default=str)}],
                      "isError": False}
        except (FilevineError, TypeError, ValueError, KeyError) as e:
            result = {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True}
    else:
        return {"jsonrpc": "2.0", "id": mid,
                "error": {"code": -32601, "message": f"Method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def main():
    server = Server()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        else:
            resp = handle(server, msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
