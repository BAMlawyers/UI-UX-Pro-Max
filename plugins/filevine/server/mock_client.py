"""In-memory stand-in for FilevineClient, backed by mock_data.json.

Used when FILEVINE_MOCK=1 so the plugin can be demoed and tested without
credentials or touching live client data.
"""

import copy
import json
import os
from datetime import datetime, timezone

from filevine_client import FilevineError

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mock_data.json")


class MockFilevineClient:
    def __init__(self, path=DATA_PATH):
        with open(path, encoding="utf-8") as f:
            self.data = json.load(f)
        self._next_note = 10_000

    def configured(self):
        return True

    def _project(self, project_id):
        for p in self.data["projects"]:
            if str(p["projectId"]["native"]) == str(project_id):
                return p
        raise FilevineError(f"Project {project_id} not found (HTTP 404)")

    def _scoped(self, key, project_id, default):
        self._project(project_id)
        return copy.deepcopy(self.data[key].get(str(project_id), default))

    def list_projects(self, limit=1000, offset=0, requested_fields=None):
        items = self.data["projects"][offset : offset + limit]
        return {"items": copy.deepcopy(items), "hasMore": offset + limit < len(self.data["projects"])}

    def get_project(self, project_id):
        return copy.deepcopy(self._project(project_id))

    def get_form(self, project_id, section):
        forms = self._scoped("forms", project_id, {})
        if section not in forms:
            raise FilevineError(f"Section '{section}' not found (HTTP 404)")
        return forms[section]

    def update_form(self, project_id, section, fields):
        form = self.data["forms"].setdefault(str(project_id), {}).setdefault(section, {})
        form.update(fields)
        return copy.deepcopy(form)

    def get_collection(self, project_id, section, limit=200):
        cols = self._scoped("collections", project_id, {})
        if section not in cols:
            raise FilevineError(f"Collection '{section}' not found (HTTP 404)")
        return {"items": cols[section][:limit]}

    def list_notes(self, project_id, limit=50):
        return {"items": self._scoped("notes", project_id, [])[:limit]}

    def create_note(self, project_id, body):
        self._project(project_id)
        self._next_note += 1
        note = {
            "noteId": {"native": self._next_note},
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "author": "Claude (mock)",
            "body": body,
        }
        self.data["notes"].setdefault(str(project_id), []).insert(0, note)
        return copy.deepcopy(note)

    def list_contacts(self, project_id):
        return {"items": self._scoped("contacts", project_id, [])}

    def list_deadlines(self, project_id):
        return {"items": self._scoped("deadlines", project_id, [])}

    def list_documents(self, project_id, limit=200):
        return {"items": self._scoped("documents", project_id, [])[:limit]}

    def list_sections(self, project_type_id):
        sections = self.data["sections"].get(str(project_type_id))
        if sections is None:
            raise FilevineError(f"Project type {project_type_id} not found (HTTP 404)")
        return {"items": [{k: v for k, v in s.items() if k != "fields"} for s in sections]}

    def get_section_schema(self, project_type_id, section):
        for s in self.data["sections"].get(str(project_type_id), []):
            if s["sectionSelector"] == section:
                return copy.deepcopy(s)
        raise FilevineError(f"Section '{section}' not found (HTTP 404)")

    def request(self, method, path, params=None, body=None):
        raise FilevineError("Raw API passthrough is not available in mock mode.")
