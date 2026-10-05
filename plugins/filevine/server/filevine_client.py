"""Filevine API v2 client (stdlib only).

Auth flow (Filevine API Gateway, v2):
  1. Exchange a Personal Access Token (PAT) + client credentials for a bearer
     token at the identity endpoint.
  2. Resolve the user ID and org ID (or take them from env).
  3. Send every request with Authorization, x-fv-orgid and x-fv-userid.

Every URL is overridable by env var so tenant-specific gateways (or a change on
Filevine's side) don't require a code change.
"""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_IDENTITY_URL = "https://identity.filevine.com/connect/token"
DEFAULT_API_BASE = "https://api.filevineapp.com/fv-app/v2"
DEFAULT_SCOPE = (
    "fv.api.gateway.access tenant filevine.v2.api.* openid email fv.auth.tenant.read"
)


class FilevineError(Exception):
    pass


def native_id(value):
    """Filevine wraps IDs as {"native": 123, "partner": null}. Unwrap them."""
    if isinstance(value, dict) and "native" in value:
        return value["native"]
    return value


def unwrap_ids(obj):
    """Recursively replace {"native": x, "partner": y} with x for readable output."""
    if isinstance(obj, dict):
        if set(obj.keys()) <= {"native", "partner"} and "native" in obj:
            return obj["native"]
        return {k: unwrap_ids(v) for k, v in obj.items() if k != "links"}
    if isinstance(obj, list):
        return [unwrap_ids(v) for v in obj]
    return obj


class FilevineClient:
    def __init__(self, env=None):
        env = env if env is not None else os.environ
        self.pat = env.get("FILEVINE_PAT", "")
        self.client_id = env.get("FILEVINE_CLIENT_ID", "")
        self.client_secret = env.get("FILEVINE_CLIENT_SECRET", "")
        self.user_id = env.get("FILEVINE_USER_ID", "")
        self.org_id = env.get("FILEVINE_ORG_ID", "")
        self.identity_url = env.get("FILEVINE_IDENTITY_URL", DEFAULT_IDENTITY_URL)
        self.api_base = env.get("FILEVINE_API_BASE", DEFAULT_API_BASE).rstrip("/")
        self.scope = env.get("FILEVINE_SCOPE", DEFAULT_SCOPE)
        self.timeout = float(env.get("FILEVINE_TIMEOUT", "30"))
        self._token = None
        self._token_expiry = 0.0

    # -- auth -------------------------------------------------------------

    def configured(self):
        return bool(self.pat and self.client_id and self.client_secret)

    def _authenticate(self):
        if not self.configured():
            raise FilevineError(
                "Filevine credentials missing. Set FILEVINE_PAT, FILEVINE_CLIENT_ID "
                "and FILEVINE_CLIENT_SECRET (or FILEVINE_MOCK=1 to use sample data)."
            )
        body = urllib.parse.urlencode(
            {
                "token": self.pat,
                "grant_type": "personal_access_token",
                "scope": self.scope,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }
        ).encode()
        req = urllib.request.Request(
            self.identity_url,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        data = self._send(req, auth_step=True)
        self._token = data["access_token"]
        self._token_expiry = time.time() + int(data.get("expires_in", 3600)) - 60

        if not (self.user_id and self.org_id):
            info = self._raw("POST", "/utils/GetUserOrgsWithToken")
            self.user_id = self.user_id or str(native_id(info["user"]["userId"]))
            orgs = info.get("orgs") or []
            if not orgs:
                raise FilevineError("Token resolved no Filevine orgs for this user.")
            self.org_id = self.org_id or str(orgs[0]["orgId"])

    def _ensure_token(self):
        if not self._token or time.time() >= self._token_expiry:
            self._authenticate()

    # -- transport --------------------------------------------------------

    def _send(self, req, auth_step=False):
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:500]
            where = "authentication" if auth_step else req.full_url
            raise FilevineError(f"Filevine {where} failed: HTTP {e.code} {detail}") from e
        except urllib.error.URLError as e:
            raise FilevineError(f"Cannot reach Filevine: {e.reason}") from e

    def _raw(self, method, path, params=None, body=None):
        url = self.api_base + "/" + path.lstrip("/")
        if params:
            clean = {k: v for k, v in params.items() if v not in (None, "")}
            if clean:
                url += "?" + urllib.parse.urlencode(clean, doseq=True)
        headers = {"Authorization": f"Bearer {self._token}", "Accept": "application/json"}
        if self.org_id:
            headers["x-fv-orgid"] = str(self.org_id)
        if self.user_id:
            headers["x-fv-userid"] = str(self.user_id)
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        return self._send(req)

    def request(self, method, path, params=None, body=None):
        self._ensure_token()
        return self._raw(method, path, params=params, body=body)

    # -- endpoints --------------------------------------------------------

    def list_projects(self, limit=1000, offset=0, requested_fields=None):
        params = {"limit": limit, "offset": offset}
        if requested_fields:
            params["requestedFields"] = ",".join(requested_fields)
        return self.request("GET", "Projects", params)

    def get_project(self, project_id):
        return self.request("GET", f"Projects/{project_id}")

    def get_form(self, project_id, section):
        return self.request("GET", f"Projects/{project_id}/Forms/{section}")

    def update_form(self, project_id, section, fields):
        return self.request("PATCH", f"Projects/{project_id}/Forms/{section}", body=fields)

    def get_collection(self, project_id, section, limit=200):
        return self.request(
            "GET", f"Projects/{project_id}/Collections/{section}", {"limit": limit}
        )

    def list_notes(self, project_id, limit=50):
        return self.request("GET", f"Projects/{project_id}/Notes", {"limit": limit})

    def create_note(self, project_id, body):
        return self.request(
            "POST", "Notes", body={"projectId": {"native": int(project_id)}, "body": body}
        )

    def list_contacts(self, project_id):
        return self.request("GET", f"Projects/{project_id}/Contacts")

    def list_deadlines(self, project_id):
        return self.request("GET", f"Projects/{project_id}/Deadlines")

    def list_documents(self, project_id, limit=200):
        return self.request("GET", f"Projects/{project_id}/Documents", {"limit": limit})

    def list_sections(self, project_type_id):
        return self.request("GET", f"ProjectTypes/{project_type_id}/Sections")

    def get_section_schema(self, project_type_id, section):
        return self.request("GET", f"ProjectTypes/{project_type_id}/Sections/{section}")
