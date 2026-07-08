"""
STEP 5a — GOOGLE SHEETS: data output.

Job: push the final enriched + personalized rows into a Google Sheet, so the
Loom can show a clean, filterable table: company, contact, title, hiring
signal, and the generated message, side by side. This is the artifact you
scroll through on camera to prove the pipeline actually ran end to end.

Requires: a Google Cloud service account with Sheets API enabled, and
GOOGLE_SERVICE_ACCOUNT_JSON env var pointing to the credentials file path.
Share the target Sheet with the service account's email address first.

Setup docs: https://docs.gspread.org/en/latest/oauth2.html
"""

import os
import sys
import json
import gspread

SHEET_NAME = os.environ.get("OUTBOUND_SHEET_NAME", "GTM Outbound Demo")

HEADERS = [
    "Company", "Domain", "Category", "Hiring Signal",
    "Contact Name", "Title", "Email", "LinkedIn", "Personalized Message",
]


def main():
    creds_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not creds_path or not os.path.exists(creds_path):
        print("ERROR: set GOOGLE_SERVICE_ACCOUNT_JSON to a valid service account key path")
        sys.exit(1)

    in_path = os.path.join(os.path.dirname(__file__), "..", "output", "step4_final_outreach.json")
    with open(in_path) as f:
        rows = json.load(f)

    gc = gspread.service_account(filename=creds_path)

    try:
        sh = gc.open(SHEET_NAME)
    except gspread.SpreadsheetNotFound:
        sh = gc.create(SHEET_NAME)
        print(f"  created new sheet '{SHEET_NAME}' -- remember to share it with your own Google account")

    ws = sh.sheet1
    ws.clear()

    table = [HEADERS]
    for r in rows:
        table.append([
            r["company"], r["domain"], r["category"], str(r["hiring_signal"]),
            r["contact_name"], r["contact_title"], r["contact_email"],
            r["linkedin_url"], r["personalized_message"],
        ])

    ws.update(table)
    print(f"\nDone. {len(rows)} rows pushed to Google Sheet '{SHEET_NAME}' -> {sh.url}")


if __name__ == "__main__":
    main()
