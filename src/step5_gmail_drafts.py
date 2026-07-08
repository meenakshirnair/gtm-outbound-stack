"""
STEP 5b — GMAIL: draft output.

Job: take the final personalized messages and create actual Gmail drafts, one
per contact, addressed and subject-lined and ready to review/send. This is
the "yes, this is genuinely demo-ready, not just a spreadsheet of text" proof
for the Loom: you open Gmail, show a stack of drafts sitting in the Drafts
folder, each one specific to a real company and person.

Requires: OAuth credentials for the Gmail API (credentials.json from Google
Cloud Console, Gmail API enabled, scope: https://www.googleapis.com/auth/gmail.compose).
First run will open a browser window for you to authorize.

Setup docs: https://developers.google.com/gmail/api/quickstart/python
"""

import os
import sys
import json
import base64
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "gmail_token.json")
CREDS_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "credentials.json")


def get_gmail_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDS_PATH):
                print(f"ERROR: place your OAuth client secret at {CREDS_PATH}")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def create_draft(service, row: dict):
    message = MIMEText(row["personalized_message"])
    message["to"] = row["contact_email"]
    message["subject"] = f"Quick thought on {row['company']}'s GTM workflow"
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    body = {"message": {"raw": raw}}
    service.users().drafts().create(userId="me", body=body).execute()


def main():
    in_path = os.path.join(os.path.dirname(__file__), "..", "output", "step4_final_outreach.json")
    with open(in_path) as f:
        rows = json.load(f)

    service = get_gmail_service()

    created = 0
    for row in rows:
        if not row.get("personalized_message"):
            continue
        try:
            create_draft(service, row)
            created += 1
            print(f"  -> draft created for {row['contact_name']} ({row['company']})")
        except Exception as e:
            print(f"  !! failed on {row['contact_name']}: {e}")

    print(f"\nDone. {created} Gmail drafts created.")


if __name__ == "__main__":
    main()
