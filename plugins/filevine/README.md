# Filevine plugin for Claude Code

Built for high-volume plaintiff PI practice. It connects Claude to Filevine through the v2 API and adds firm workflows on top.

| Command | What it does |
|---|---|
| `/fv-brief <client or case #>` | One-screen case brief: liability, treatment, specials, coverage, SOL, weakest point, next actions |
| `/fv-sol [phase]` | Risk-ranked SOL and governmental notice-of-claim audit for UT, ID and AZ, with citations |
| `/fv-demand <client or case #>` | Demand-readiness check (blockers with owners), specials table, coverage analysis, demand outline |
| `/fv-template <doc or broken template>` | Drafts a Liquid doc-assembly template from your tenant's real selectors and lints it |
| `/fv-note <case> <text>` | Drafts a case note and posts it only after you confirm |

## Architecture

```
plugins/filevine/
├── .claude-plugin/plugin.json   plugin manifest
├── .mcp.json                    registers the MCP server (python3, stdlib only, no installs)
├── server/
│   ├── filevine_mcp.py          MCP stdio server, 17 tools
│   ├── filevine_client.py       v2 API client: PAT → bearer token, org/user headers
│   ├── mock_client.py           offline client backed by mock_data.json (fictional cases)
│   ├── sol.py                   SOL / notice-of-claim rules table (UT, ID, AZ)
│   └── liquid_lint.py           static checker for Liquid templates
├── skills/                      fv-case-brief, fv-sol-audit, fv-demand-prep, fv-liquid-drafting
├── commands/                    slash-command entry points
└── tests/test_filevine.py       20 tests (python3 -m unittest)
```

**Tools:** `filevine_status`, `filevine_search_projects`, `filevine_get_project`, `filevine_case_snapshot`, `filevine_get_section`, `filevine_get_collection`, `filevine_list_notes`, `filevine_list_contacts`, `filevine_list_deadlines`, `filevine_list_documents`, `filevine_list_sections`, `filevine_get_section_schema`, `filevine_sol_check`, `filevine_lint_template`, `filevine_api_get` (read-only passthrough), and the write tools `filevine_create_note` and `filevine_update_section`.

## Setup

1. In Filevine, create an API key pair (Client ID and Client Secret) and a Personal Access Token. An org admin may need to enable API access.
2. Export the credentials in the shell that launches Claude Code:
   ```bash
   export FILEVINE_PAT=...
   export FILEVINE_CLIENT_ID=...
   export FILEVINE_CLIENT_SECRET=...
   # optional: skip the org/user lookup
   export FILEVINE_ORG_ID=... FILEVINE_USER_ID=...
   ```
3. Install the plugin:
   ```
   /plugin marketplace add bamlawyers/ui-ux-pro-max
   /plugin install filevine
   ```
4. Run `filevine_status` (or ask "is Filevine connected?") to confirm.

**Try it without credentials:** `export FILEVINE_MOCK=1` loads three fictional cases: a UT rear-end with a commercial truck, an ID municipal trip-and-fall that hits the ITCA notice deadline in October 2026, and a UT minor dog-bite case in litigation.

## Safety model

- **Read-only by default.** Writes need `FILEVINE_ALLOW_WRITES=1`. Even then, the tool descriptions and skills require Claude to show you the exact note text, or a from/to field table, and wait for your yes.
- `filevine_update_section` returns a from/to diff for every changed field.
- `filevine_api_get` only accepts relative GET paths, so it can't be pointed at another host.
- **Client data is PHI and privileged.** Everything a tool returns goes into the Claude conversation. Before rollout, confirm your Anthropic plan terms (BAA/zero-retention), your Filevine API terms, and your firm's data policy cover this use. Use a dedicated API user with least-privilege access, not a partner's account.
- The SOL tool is a docket-control aid. It returns raw dates with no weekend roll-forward, lists minority tolling next to the untolled date and never in place of it, and marks every row `verify: true`.

## Tenant configuration

Section and field selectors differ from one Filevine org to the next. The defaults (`intake`, `insurance`, `litigation`, `meds`; `billed`/`paid` for specials) match the mock data only. The skills discover your real selectors with `filevine_list_sections` and `filevine_get_section_schema`. To change the specials columns, set `FILEVINE_BILLED_FIELD` and `FILEVINE_PAID_FIELD`. If your gateway differs, override the endpoints with `FILEVINE_API_BASE`, `FILEVINE_IDENTITY_URL` or `FILEVINE_SCOPE`.

## Development

```bash
cd plugins/filevine
python3 -m unittest tests/test_filevine.py -v
FILEVINE_MOCK=1 python3 server/filevine_mcp.py   # speak JSON-RPC on stdin
```
