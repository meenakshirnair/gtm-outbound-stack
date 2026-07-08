"""
STEP 4 — GEMINI API: message personalization.

Job: for each enriched contact, write a short, specific outbound email that
references something real about their company (the hiring signal from step 3,
or a page snippet from step 1) instead of a generic template. This is the
step that turns "we scraped some data" into "we produced something a rep
could actually send."

Requires: GEMINI_API_KEY env var. Get one free at https://aistudio.google.com/apikey
"""

import os
import sys
import json
import time
import google.generativeai as genai

GEMINI_MODEL = "gemini-2.0-flash"

PROMPT_TEMPLATE = """You are writing a short, specific cold outbound email from a GTM Engineer \
at InRule Technology (decision automation software) to a prospect at another company.

Prospect: {name}, {title} at {company_name} ({category}).
Signal we found: {signal_context}

Write a 3-4 sentence cold email. Reference the specific signal naturally, not \
as a gimmick. No generic flattery. No em dashes. Plain, direct, confident tone. \
End with a soft, specific call to action (e.g. suggesting a 15-minute call), \
not "let me know if interested."

Return ONLY the email body, no subject line, no preamble."""


def build_signal_context(company: dict) -> str:
    if company.get("hiring_signal"):
        kws = ", ".join(company.get("matched_keywords", []))
        return f"Their careers page shows active hiring signal around: {kws}."
    pages = company.get("scraped_pages", [])
    if pages and pages[0].get("text"):
        return f"From their site: {pages[0]['text'][:300]}"
    return "No strong signal found; keep the email general to their industry."


def personalize(model, company: dict, contact: dict) -> str:
    prompt = PROMPT_TEMPLATE.format(
        name=contact["name"],
        title=contact["title"],
        company_name=company["name"],
        category=company["category"],
        signal_context=build_signal_context(company),
    )
    response = model.generate_content(prompt)
    return response.text.strip()


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: set GEMINI_API_KEY in your environment (see config/.env.example)")
        sys.exit(1)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(GEMINI_MODEL)

    in_path = os.path.join(os.path.dirname(__file__), "..", "output", "step3_signal_checked.json")
    with open(in_path) as f:
        companies = json.load(f)

    final_rows = []
    for company in companies:
        for contact in company.get("contacts", []):
            if not contact.get("email"):
                continue
            print(f"  -> writing message for {contact['name']} ({company['name']})...")
            try:
                message = personalize(model, company, contact)
            except Exception as e:
                print(f"  !! failed on {contact['name']}: {e}")
                message = ""
            final_rows.append({
                "company": company["name"],
                "domain": company["domain"],
                "category": company["category"],
                "hiring_signal": company.get("hiring_signal", False),
                "contact_name": contact["name"],
                "contact_title": contact["title"],
                "contact_email": contact["email"],
                "linkedin_url": contact.get("linkedin_url", ""),
                "personalized_message": message,
            })
            time.sleep(0.5)

    out_path = os.path.join(os.path.dirname(__file__), "..", "output", "step4_final_outreach.json")
    with open(out_path, "w") as f:
        json.dump(final_rows, f, indent=2)

    print(f"\nDone. {len(final_rows)} personalized messages -> {out_path}")


if __name__ == "__main__":
    main()
