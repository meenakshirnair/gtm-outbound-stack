"""
STEP 2 — HUNTER.IO: person-level enrichment.

Job: for each target company, hit Hunter's Domain Search API to find real
recruiters/hiring managers/talent acquisition people, with verified emails
included directly in the response (no separate enrichment call needed,
unlike Apollo).

This pipeline is for personal job-search outreach: finding the right person
at a target company to reach out to about open roles, not a sales/GTM
prospecting tool. The same underlying architecture (Apify -> Hunter ->
Puppeteer -> Gemini -> Sheets/Gmail) applies either way — only WHO we're
searching for and WHAT the message says changes.

Switched to Hunter from Apollo because Apollo's Search API is gated entirely
behind a paid plan (returns a hard 403 `API_INACCESSIBLE` on free tier, even
with unused credits sitting in the account — credits and API access are
separate entitlements on Apollo). Hunter's free forever plan includes real
API access with no separate gate.

Note: Hunter's department taxonomy doesn't have a dedicated "recruiting"
bucket, so this script does keyword matching on job titles first, and falls
back to HR/People-adjacent or senior generalist roles if no exact recruiter
title exists at a given company — not every company has someone with
"recruiter" literally in their title, especially smaller ones where hiring
runs through a generalist HR or ops role.

Requires: HUNTER_API_KEY env var. Get one free at https://hunter.io/api-keys
"""

import os
import sys
import json
import time
import requests

HUNTER_API_KEY = os.environ.get("HUNTER_API_KEY")
HUNTER_SEARCH_URL = "https://api.hunter.io/v2/domain-search"

# Keywords checked against each person's raw title, in priority order.
TITLE_KEYWORDS = [
    "recruiter", "recruiting", "talent acquisition", "talent partner",
    "people operations", "hr business partner", "human resources",
    "hiring manager", "people team", "talent scout",
]

# Fallback: if no title keyword match, prefer these departments so we still
# get a sensible contact rather than an empty result — a lot of mid-market
# companies route hiring through HR generalists or leadership, not a
# dedicated recruiter.
FALLBACK_DEPARTMENTS = {"hr", "executive", "management"}


def search_domain(domain: str, limit: int = 10) -> list:
    params = {"domain": domain, "api_key": HUNTER_API_KEY, "limit": limit}
    resp = requests.get(HUNTER_SEARCH_URL, params=params, timeout=30)
    if not resp.ok:
        print(f"    Hunter response body: {resp.text[:500]}")
    resp.raise_for_status()
    return resp.json().get("data", {}).get("emails", [])


def pick_contacts(people: list, max_contacts: int = 2) -> list:
    """Prioritize recruiter/HR keyword matches, fall back to senior generalists."""
    def title_of(p):
        return (p.get("position_raw") or p.get("position") or "").lower()

    keyword_matches = [
        p for p in people
        if any(kw in title_of(p) for kw in TITLE_KEYWORDS)
    ]
    if keyword_matches:
        chosen = keyword_matches[:max_contacts]
    else:
        fallback = [
            p for p in people
            if (p.get("department") or "").lower() in FALLBACK_DEPARTMENTS
        ]
        chosen = (fallback or people)[:max_contacts]

    return [
        {
            "name": f"{p.get('first_name', '')} {p.get('last_name', '')}".strip(),
            "title": p.get("position_raw") or p.get("position") or "Unknown",
            "email": p.get("value"),
            "linkedin_url": p.get("linkedin") or "",
        }
        for p in chosen
        if p.get("value")  # only keep people with an actual email
    ]


def main():
    if not HUNTER_API_KEY:
        print("ERROR: set HUNTER_API_KEY in your environment (see config/.env.example)")
        sys.exit(1)

    in_path = os.path.join(os.path.dirname(__file__), "..", "output", "step1_scraped_companies.json")
    with open(in_path) as f:
        companies = json.load(f)

    enriched = []
    for company in companies:
        print(f"  -> enriching {company['name']}...")
        try:
            people = search_domain(company["domain"], limit=10)
            contacts = pick_contacts(people, max_contacts=2)
        except requests.exceptions.HTTPError as e:
            print(f"  !! failed on {company['name']}: {e}")
            contacts = []
        enriched.append({**company, "contacts": contacts})
        time.sleep(1)  # be polite to Hunter's rate limits

    out_path = os.path.join(os.path.dirname(__file__), "..", "output", "step2_enriched_contacts.json")
    with open(out_path, "w") as f:
        json.dump(enriched, f, indent=2)

    total_contacts = sum(len(c["contacts"]) for c in enriched)
    print(f"\nDone. {total_contacts} contacts found across {len(enriched)} companies -> {out_path}")


if __name__ == "__main__":
    main()
