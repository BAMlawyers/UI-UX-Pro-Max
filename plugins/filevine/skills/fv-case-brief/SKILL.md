---
name: fv-case-brief
description: Pull a Filevine personal-injury case and produce an attorney-ready case brief — liability, injuries/treatment, specials, coverage, deadlines, and the weakest point of the case. Use when asked to "brief me on", "where are we on", "summarize the file for", or "prep me for a call on" a client or case number.
---

# Filevine Case Brief

Produce a one-screen brief a partner can read before a call, mediation, or case review.

## Steps

1. **Find the case.** `filevine_search_projects` with the client name or case number. If more than one match, list them (name, number, phase) and ask which — never guess between two clients.
2. **Pull everything in one call.** `filevine_case_snapshot` with the project ID. If the tenant's section selectors differ from the defaults (`intake`, `insurance`, `litigation`, `meds`), call `filevine_list_sections` with the project's `projectTypeId` and re-run with the right selectors. Note anything in `missing`.
3. **Run the SOL check.** `filevine_sol_check` using the incident state, incident date, governmental-entity flag, and client DOB from the snapshot. A deadline the tool returns always beats one inferred from notes.
4. **Write the brief** in this order:

```
CLIENT v. DEFENDANT — Case # — Phase
SOL: <earliest deadline> (<days> days, <status>) — <citation>   [⚠ if CRITICAL/URGENT/EXPIRED]

LIABILITY     2–3 sentences. Facts + evidence (police report, citation, witnesses).
INJURIES/TX   Providers in date order; flag gaps in treatment > 30 days and anyone still treating.
SPECIALS      Billed $X / Paid $Y across N providers. Records/bills outstanding: list.
COVERAGE      Def carrier + limits; client PIP/UIM. Flag limits that cap the case.
LITIGATION    Court, case no., judge, next deadline (if filed).
RECENT        Last 3 notes, one line each, with date.
WEAKEST POINT The single fact defense counsel or the adjuster attacks first, and why.
NEXT ACTIONS  3 concrete tasks, each with an owner role (attorney / CM / paralegal).
```

## Rules

- Report only what the file says. If a field is blank, write "not in file" — don't fill gaps from inference.
- Always surface treatment gaps, pre-existing-condition notes, and coverage that is less than specials. Those decide the case value.
- Minor client: note guardian, and that settlement likely needs court approval. Verify the jurisdiction's minor-settlement procedure.
- This is PHI. Don't paste the brief anywhere outside the conversation unless the user asks.
