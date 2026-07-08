"""
STEP 2 — APOLLO: person-level enrichment.

Job: for each scraped company, hit Apollo's People Search API filtered to
RevOps / GTM titles, and pull back name, title, verified email, and LinkedIn URL.

Apify told us WHICH companies to look at. Apollo tells us WHO at those
companies to actually talk to. This is the classic two-tool split in a real
outbound stack: a scraper for company-level discovery, a data provider
(Apollo/ZoomInfo/Clearbit) for person-level contact data — because scrapers are
bad at finding verified emails, and contact databases are bad at reading a
website's actual content.

Requires: APOLLO_API_KEY env var. Get one at https://app.apollo.io/#/settings/integrations/api
"""

import os
import sys
import json
import time
import requests

APOLLO_API_KEY = os.environ.get("APOLLO_API_KEY")
APOLLO_SEARCH_URL = "https://api.apollo.io/api/v1/mixed_people/search"

TARGET_TITLES = [
    "Director of Revenue Operations",
    "VP of Revenue Operations",
    "Head of GTM",
    "GTM Engineer",
    "Director of Sales Operations",
    "RevOps Manager",
]


def find_contacts(domain: str) -> list:
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": APOLLO_API_KEY,
    }
    payload = {
        "q_organization_domains": domain,
        "person_titles": TARGET_TITLES,
        "page": 1,
        "per_page": 3,
    }
    resp = requests.post(APOLLO_SEARCH_URL, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    contacts = []
    for person in data.get("people", []):
        contacts.append({
            "name": person.get("name"),
            "title": person.get("title"),
            "email": person.get("email"),
            "linkedin_url": person.get("linkedin_url"),
        })
    return contacts


def main():
    if not APOLLO_API_KEY:
        print("ERROR: set APOLLO_API_KEY in your environment (see config/.env.example)")
        sys.exit(1)

    in_path = os.path.join(os.path.dirname(__file__), "..", "output", "step1_scraped_companies.json")
    with open(in_path) as f:
        companies = json.load(f)

    enriched = []
    for company in companies:
        print(f"  -> enriching {company['name']}...")
        try:
            contacts = find_contacts(company["domain"])
        except Exception as e:
            print(f"  !! failed on {company['name']}: {e}")
            contacts = []
        enriched.append({**company, "contacts": contacts})
        time.sleep(1)  # respect Apollo rate limits

    out_path = os.path.join(os.path.dirname(__file__), "..", "output", "step2_enriched_contacts.json")
    with open(out_path, "w") as f:
        json.dump(enriched, f, indent=2)

    total_contacts = sum(len(c["contacts"]) for c in enriched)
    print(f"\nDone. {total_contacts} contacts found across {len(enriched)} companies -> {out_path}")


if __name__ == "__main__":
    main()
