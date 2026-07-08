"""
STEP 1 — APIFY: company-level scraping.

Job: for each seed company, run Apify's Website Content Crawler actor against
their /careers and /about (or /leadership) pages. We're pulling raw text back,
which step 3 (Puppeteer) and later Claude will read for GTM/RevOps hiring signal.

Why Apify here and not requests+BeautifulSoup: most SaaS marketing sites are
JS-rendered (React/Next.js), so a plain HTTP GET returns an empty shell. Apify's
actor runs a real headless browser on their infra and handles JS rendering,
proxies, and retries for us, which is exactly why a GTM team would reach for it
over rolling their own scraper.

Requires: APIFY_TOKEN env var. Get one free at https://console.apify.com/account/integrations
"""

import os
import sys
import json
import time
from apify_client import ApifyClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.target_companies import TARGET_COMPANIES

APIFY_TOKEN = os.environ.get("APIFY_TOKEN")
ACTOR_ID = "apify/website-content-crawler"


def scrape_company(client: ApifyClient, company: dict) -> dict:
    """Run the Website Content Crawler against a single company's key pages."""
    start_urls = [
        {"url": f"https://{company['domain']}/careers"},
        {"url": f"https://{company['domain']}/about"},
    ]

    run_input = {
        "startUrls": start_urls,
        "maxCrawlPages": 4,
        "crawlerType": "playwright:chrome",  # handles JS-rendered pages
    }

    print(f"  -> scraping {company['name']} ({company['domain']})...")
    run = client.actor(ACTOR_ID).call(run_input=run_input)

    pages = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        pages.append({
            "url": item.get("url"),
            "text": (item.get("text") or "")[:4000],  # cap for downstream token budget
        })

    return {**company, "scraped_pages": pages}


def main():
    if not APIFY_TOKEN:
        print("ERROR: set APIFY_TOKEN in your environment (see config/.env.example)")
        sys.exit(1)

    client = ApifyClient(APIFY_TOKEN)
    results = []

    for company in TARGET_COMPANIES:
        try:
            results.append(scrape_company(client, company))
        except Exception as e:
            print(f"  !! failed on {company['name']}: {e}")
            results.append({**company, "scraped_pages": [], "error": str(e)})
        time.sleep(1)  # be polite to the actor queue

    out_path = os.path.join(os.path.dirname(__file__), "..", "output", "step1_scraped_companies.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nDone. {len(results)} companies scraped -> {out_path}")


if __name__ == "__main__":
    main()
