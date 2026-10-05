---
name: fv-liquid-drafting
description: Draft and lint Filevine document-assembly templates using Liquid tokens (client.*, litigation.*, custom sections, filters like | capitalize). Use when building or fixing a Filevine doc-gen template — letters of representation, demand letters, complaints, discovery, subpoenas, notices of claim — or when a template "won't merge" or prints blank fields.
---

# Filevine Liquid Template Drafting

## Ground truth comes from the tenant, not memory

Token paths are `section.field` built from **selectors**, and selectors are tenant-specific. Before writing tokens:

1. Get the project type: `filevine_get_project` on any case of that type → `projectTypeId`.
2. `filevine_list_sections` → section selectors. `filevine_get_section_schema` for each section you use → field selectors and types.
3. Use only selectors those tools return. If a needed field doesn't exist, say so and propose adding it in Filevine Admin, rather than inventing a token.

`client.*` and `project.*` are built-in roots. Confirm the exact client field names (e.g. `client.fullname`, `client.firstname`) against a merged sample in the tenant before relying on them.

## Drafting conventions

- Names: `{{ client.fullname | capitalize }}` for captions only if the tenant stores names in lower case; otherwise leave as stored. `| upcase` for caption party names where the court format calls for caps.
- Dates: `{{ litigation.complaintFiledDate | date: "%B %-d, %Y" }}`.
- Money: Liquid has no currency filter. Store currency formatted, or build it with `round: 2` and a `$` prefix — and say which you did.
- Guard every optional field: `{% if insurance.claimNumber %}Claim No. {{ insurance.claimNumber }}{% endif %}`. A blank merge in a demand letter is worse than an omitted line.
- Defaults for placeholders the paralegal must fill: `{{ litigation.judge | default: "[JUDGE]" }}` so gaps are visible in the output.
- Collections: `{% for m in meds %}{{ m.provider }} — {{ m.billed }}{% endfor %}`.
- Straight quotes only inside `{{ }}` / `{% %}`. Word's smart quotes and autocorrect-split braces are the #1 cause of broken templates.
- Match the jurisdiction's caption and format (Utah URCP, Idaho IRCP, Arizona ARCP); state which rule set you followed.

## Always lint before handing back

Run `filevine_lint_template` with the full template and the `projectTypeId`. Fix every error. Report warnings you're leaving in place and why. Hand back:

1. The template.
2. A token map: token → section/field name → what it prints.
3. Lint result (should be `ok: true`).
