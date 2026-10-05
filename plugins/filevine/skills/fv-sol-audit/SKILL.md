---
name: fv-sol-audit
description: Audit Filevine cases for statute-of-limitations and governmental notice-of-claim exposure (UT, ID, AZ) and produce a risk-ranked docket report. Use for "SOL audit", "what's about to blow", "check deadlines", "notice of claim", or before a phase or caseload review.
---

# SOL / Notice-of-Claim Audit

A missed SOL is the firm's biggest malpractice exposure. This skill finds it before it happens.

## Steps

1. **Scope.** All open cases, one phase (`phase` filter on `filevine_search_projects`), or a list the user gives. Pre-litigation phases are where the risk is — default to every phase except litigation/closed if the user doesn't say.
2. **Pull per case:** `filevine_get_project` (incident date) and `filevine_get_section` for the intake section (incident state, governmental entity, client DOB) and litigation section (complaint filed date). If selectors differ in this tenant, find them with `filevine_list_sections` / `filevine_get_section_schema` once, then reuse.
3. **Compute:** `filevine_sol_check` per case. Add `med_mal`, `wrongful_death` or `property_damage` to `claim_types` when the case type calls for it.
4. **Classify:**
   - Complaint already filed → SOL satisfied for named defendants; flag only if notes mention adding a party (relation-back risk).
   - `governmental_entity` true → notice-of-claim deadline is usually the earliest. Treat it as the controlling date.
   - Missing incident date or state → **DATA GAP**, ranked right below EXPIRED. A case you can't compute is a case you can't protect.
5. **Report** as a table sorted by days remaining:

| Status | Case | Client | Claim | Deadline | Days | Cite | Filed? | Action |

   Then: count by status, the data-gap list, and minors with tolling notes listed separately.
6. **Optional write-back** (only if the user asks, and writes are enabled): offer to set the litigation SOL field with `filevine_update_section`. Show the from/to table first and wait for an explicit yes. Never overwrite a non-empty SOL field without calling out the difference.

## Non-negotiables

- The tool is a docket-control aid, not the answer. Every row says **verify**. Rules can't see discovery-rule facts, tolling agreements, a defendant out of state, or amendments after the rules table was written.
- Raw dates only. Don't roll a weekend deadline forward in the report.
- Minority tolling is shown next to the untolled date, never instead of it. Recommend calendaring the untolled date until an attorney signs off.
- Governmental claims: UT, ID and AZ notice periods are short and strictly enforced. Name the entity and statute, and flag that service on the wrong agent can be fatal.
- States outside UT/ID/AZ return an error. Say so; don't estimate.
