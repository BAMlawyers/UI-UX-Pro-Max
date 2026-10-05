"""Conservative statute-of-limitations / notice-of-claim calculator.

Design rules:
  * Every result carries a citation and verify=True. This is a docket-control
    aid, not legal advice: statutes get amended and a rules table can't see
    discovery-rule, tolling or estoppel facts.
  * Raw dates only. No weekend/holiday roll-forward is applied -- calendar the
    raw date.
  * Minority tolling is reported alongside the untolled date, never instead of
    it. Calendar the untolled date unless an attorney signs off.
"""

from datetime import date, datetime, timedelta

# period: ("years", n) or ("days", n)
RULES = {
    "UT": {
        "personal_injury": {
            "period": ("years", 4),
            "cite": "Utah Code § 78B-2-307(3)",
            "notes": "General negligence. Confirm no shorter specific statute applies.",
        },
        "wrongful_death": {
            "period": ("years", 2),
            "cite": "Utah Code § 78B-2-304(2)",
            "notes": "Runs from date of death, not date of injury.",
        },
        "property_damage": {
            "period": ("years", 3),
            "cite": "Utah Code § 78B-2-305",
            "notes": "",
        },
        "med_mal": {
            "period": ("years", 2),
            "cite": "Utah Code § 78B-3-404",
            "notes": "2 years from discovery, 4-year repose from act. Notice of intent "
            "(§ 78B-3-412) and prelitigation panel (§ 78B-3-416) are prerequisites.",
        },
        "gov_notice": {
            "period": ("years", 1),
            "cite": "Utah Code §§ 63G-7-401, -402",
            "notes": "Notice of claim to the correct agent of the governmental entity. "
            "Suit deadline after denial runs separately under § 63G-7-403 -- calendar on denial.",
        },
    },
    "ID": {
        "personal_injury": {
            "period": ("years", 2),
            "cite": "Idaho Code § 5-219(4)",
            "notes": "",
        },
        "wrongful_death": {
            "period": ("years", 2),
            "cite": "Idaho Code § 5-219(4)",
            "notes": "Runs from date of death.",
        },
        "property_damage": {
            "period": ("years", 3),
            "cite": "Idaho Code § 5-218",
            "notes": "",
        },
        "med_mal": {
            "period": ("years", 2),
            "cite": "Idaho Code § 5-219(4)",
            "notes": "Prelitigation screening panel required (Idaho Code § 6-1001); "
            "filing with the Board of Medicine tolls.",
        },
        "gov_notice": {
            "period": ("days", 180),
            "cite": "Idaho Code §§ 6-905, 6-906",
            "notes": "ITCA notice: 180 days from when the claim arose or reasonably should "
            "have been discovered. § 6-905 (state) vs § 6-906 (political subdivision). "
            "Suit within 2 years (§ 6-911).",
        },
    },
    "AZ": {
        "personal_injury": {
            "period": ("years", 2),
            "cite": "A.R.S. § 12-542(1)",
            "notes": "",
        },
        "wrongful_death": {
            "period": ("years", 2),
            "cite": "A.R.S. § 12-542(2)",
            "notes": "Runs from date of death.",
        },
        "property_damage": {
            "period": ("years", 2),
            "cite": "A.R.S. § 12-542(3)",
            "notes": "",
        },
        "med_mal": {
            "period": ("years", 2),
            "cite": "A.R.S. § 12-542",
            "notes": "Discovery rule applies. Preliminary expert affidavit (§ 12-2603).",
        },
        "gov_notice": {
            "period": ("days", 180),
            "cite": "A.R.S. § 12-821.01(A)",
            "notes": "Notice of claim with specific settlement amount and supporting facts. "
            "Suit against public entity within 1 year (A.R.S. § 12-821).",
        },
    },
}

MINORITY_CITES = {
    "UT": "Utah Code § 78B-2-108",
    "ID": "Idaho Code § 5-230",
    "AZ": "A.R.S. § 12-502",
}

CLAIM_TYPES = sorted({ct for s in RULES.values() for ct in s})


def parse_date(value):
    if isinstance(value, date):
        return value
    if not value:
        return None
    text = str(value).strip()[:10]
    return datetime.strptime(text, "%Y-%m-%d").date()


def add_years(d, years):
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # Feb 29 -> Feb 28 (earlier, i.e. conservative)
        return d.replace(year=d.year + years, day=28)


def add_period(d, period):
    unit, n = period
    if unit == "years":
        return add_years(d, n)
    return d + timedelta(days=n)


def urgency(days_left):
    if days_left < 0:
        return "EXPIRED"
    if days_left <= 30:
        return "CRITICAL"
    if days_left <= 90:
        return "URGENT"
    if days_left <= 180:
        return "WATCH"
    return "OK"


def compute(state, incident_date, claim_types=None, governmental_entity=False,
            client_dob=None, date_of_death=None, today=None):
    state = (state or "").upper().strip()
    if state not in RULES:
        return {
            "error": f"No SOL rules loaded for '{state}'. Supported: {', '.join(sorted(RULES))}. "
            "Add the jurisdiction to server/sol.py before relying on this tool.",
        }
    incident = parse_date(incident_date)
    if not incident:
        return {"error": "incident_date is required (YYYY-MM-DD)."}
    today = parse_date(today) or date.today()
    dob = parse_date(client_dob)
    death = parse_date(date_of_death)

    types = list(claim_types or ["personal_injury"])
    if governmental_entity and "gov_notice" not in types:
        types.append("gov_notice")

    results = []
    for ct in types:
        rule = RULES[state].get(ct)
        if not rule:
            results.append({"claim_type": ct, "error": f"No rule for {ct} in {state}."})
            continue
        trigger = incident
        trigger_label = "incident date"
        if ct == "wrongful_death":
            if not death:
                results.append({
                    "claim_type": ct,
                    "error": "date_of_death required for wrongful death.",
                })
                continue
            trigger, trigger_label = death, "date of death"
        deadline = add_period(trigger, rule["period"])
        days_left = (deadline - today).days
        entry = {
            "claim_type": ct,
            "trigger": f"{trigger_label} {trigger.isoformat()}",
            "deadline": deadline.isoformat(),
            "days_remaining": days_left,
            "status": urgency(days_left),
            "citation": rule["cite"],
            "notes": rule["notes"],
            "verify": True,
        }
        if dob and ct != "gov_notice":
            eighteenth = add_years(dob, 18)
            if eighteenth > trigger:
                tolled = add_period(eighteenth, rule["period"])
                entry["minority_tolled_deadline"] = tolled.isoformat()
                entry["minority_note"] = (
                    f"Client was a minor on the trigger date. Tolling under "
                    f"{MINORITY_CITES[state]} may extend to {tolled.isoformat()}, "
                    "but verify scope (med mal and claim-specific limits differ). "
                    "Calendar the untolled deadline unless an attorney signs off."
                )
        if dob and ct == "gov_notice" and add_years(dob, 18) > trigger:
            entry["minority_note"] = (
                "Minor claimant on a governmental claim: do NOT assume minority tolls "
                "the notice period. Verify before relying on anything later."
            )
        results.append(entry)

    dated = [r for r in results if "deadline" in r]
    earliest = min(dated, key=lambda r: r["deadline"]) if dated else None
    return {
        "state": state,
        "as_of": today.isoformat(),
        "deadlines": results,
        "earliest": earliest,
        "disclaimer": "Docket-control aid only. Raw dates, no weekend/holiday roll. "
        "Verify every citation against current statute before calendaring.",
    }
