---
name: fv-demand-prep
description: Assess demand-readiness for a Filevine PI case and build the demand package outline — specials table, records/bills gaps, coverage analysis, and a draft demand structure. Use for "is this ready for demand", "build the demand", "specials summary", or "what are we missing before demand".
---

# Demand Prep

## Steps

1. `filevine_case_snapshot` for the case (include the lien/subrogation collection if the tenant has one — find it with `filevine_list_sections`).
2. **Readiness gate.** The case is *not* demand-ready if any of these are true; list each blocker with an owner:
   - Any provider still treating, or no MMI / discharge note.
   - Any provider with bills or records not received.
   - Liens/subrogation (health plan, Medicare/Medicaid, ERISA, hospital lien) unidentified. Medicare status unknown is a blocker.
   - Lost-wage documentation missing where notes mention missed work.
   - SOL inside 120 days — then the call is file vs. demand, not demand prep. Run `filevine_sol_check` and say so first.
3. **Specials table:** provider | dates of service | billed | paid/adjusted | records? | bills? — with totals. Use the snapshot's `specials` totals; reconcile against the rows and flag any mismatch.
4. **Coverage analysis:** specials vs. defendant limits vs. client UIM. If billed specials approach or exceed limits, recommend a policy-limits demand and flag the UIM consent/notice requirements under the client's policy (verify the policy language and jurisdiction).
5. **Draft demand outline:** liability → injuries and treatment chronology → specials → general damages narrative points (from notes: pain, ADL limits, missed events) → demand amount placeholder `[DEMAND]` → response deadline. Leave the number to the attorney.

## Rules

- Don't state a demand amount or case value unless the user asks for a valuation; if asked, give the reasoning and the weakest point together.
- Utah PIP: note whether the tort threshold is met (verify the current threshold under Utah Code § 31A-22-309). Idaho and Arizona have no PIP threshold — don't import Utah rules into ID/AZ cases.
- Treatment gaps and prior injuries go in a "defense will argue" box. Hiding them from the attorney helps no one.
