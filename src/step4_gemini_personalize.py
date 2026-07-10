"""
STEP 4 — GEMINI API: message personalization.

Job: for each enriched contact (a recruiter/hiring contact), write a short,
specific job-search outreach email that references something real about
their company (a matching open role from step 3's signal check, or a page
snippet from step 1) instead of a generic template. This is personal
job-search outreach — the email introduces Meenakshi as a candidate, not a
product pitch.

Requires: GEMINI_API_KEY env var. Get one free at https://aistudio.google.com/apikey
"""

import os
import sys
import json
import time
import google.generativeai as genai

GEMINI_MODEL = "gemini-flash-latest"
GEMINI_FALLBACK_MODEL = "gemini-flash-lite-latest"  # separate quota pool, always-current alias

PROMPT_TEMPLATE = """You are writing a short, specific job-search outreach email on behalf of \
Meenakshi Rajeev Nair, a recent MSBA graduate (W.P. Carey School of Business, Arizona State \
University, December 2025, 4.0 GPA) with 2.5 years of experience as a Software Engineer at \
Ernst & Young, where she worked on AI chatbot development using Azure Bot Framework, C#, \
backend APIs, and NLP pipelines. She is job searching for Product Analyst, Technical Business \
Analyst, AI/ML Business Analyst, Systems Analyst, and GTM Engineer roles, is open to \
relocating, and will need H1B sponsorship (not a blocker for applying).

Recipient: {name}, {title} at {company_name} ({category}).
Signal we found: {signal_context}

Write a 3-4 sentence outreach email to this recruiter/hiring contact. If the signal mentions \
a specific open role, reference it naturally and ask specifically about that role. If there's \
no specific role signal, briefly mention her background and ask if they have any openings in \
her target areas. Connect her real background (software engineering + applied AI/chatbot work \
+ the MSBA) to why she'd be a strong fit, without overselling or inventing skills she doesn't \
have. No generic flattery. No em dashes. Plain, direct, confident tone. End with a soft, \
specific call to action (e.g. asking for a brief call, or asking whether they're currently \
hiring for a relevant role), not "let me know if interested."

Return ONLY the email body, no subject line, no preamble."""

# Markers that indicate scraped text is actually an error/404 page, not real
# site content. Apify sometimes successfully "scrapes" a broken link and
# hands back the error page's own text, which looks like data but isn't —
# without this filter, that garbage gets treated as a genuine signal and the
# model writes something that sounds plausible but references nothing real.
ERROR_PAGE_MARKERS = [
    "404", "page not found", "not found", "missing or removed",
    "doesn't exist", "does not exist", "up and down arrows to select",
]


def is_error_page(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in ERROR_PAGE_MARKERS)


def build_signal_context(company: dict) -> str:
    if company.get("hiring_signal"):
        kws = ", ".join(company.get("matched_keywords", []))
        return f"Their careers page shows active hiring signal around: {kws}."

    for page in company.get("scraped_pages", []):
        text = page.get("text", "")
        if text and not is_error_page(text):
            return f"From their site: {text[:300]}"

    return "No strong signal found; keep the email general to their industry."


class DailyQuotaExhausted(Exception):
    """Raised when the free tier's daily request cap is hit (not just per-minute)."""
    pass


def personalize(model, company: dict, contact: dict, max_retries: int = 3) -> str:
    prompt = PROMPT_TEMPLATE.format(
        name=contact["name"],
        title=contact["title"],
        company_name=company["name"],
        category=company["category"],
        signal_context=build_signal_context(company),
    )

    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            err_str = str(e)
            is_rate_limit = "429" in err_str or "ResourceExhausted" in type(e).__name__
            is_daily_cap = "PerDay" in err_str

            if is_daily_cap:
                # Waiting won't help here, it resets at midnight Pacific.
                # Let the caller decide whether to switch to the fallback model.
                raise DailyQuotaExhausted(err_str)

            if is_rate_limit and attempt < max_retries - 1:
                wait_seconds = 15 * (attempt + 1)
                print(f"    rate limited, waiting {wait_seconds}s before retry "
                      f"({attempt + 1}/{max_retries})...")
                time.sleep(wait_seconds)
            else:
                raise


def make_row(company: dict, contact: dict, message: str) -> dict:
    return {
        "company": company["name"],
        "domain": company["domain"],
        "category": company["category"],
        "hiring_signal": company.get("hiring_signal", False),
        "contact_name": contact["name"],
        "contact_title": contact["title"],
        "contact_email": contact["email"],
        "linkedin_url": contact.get("linkedin_url", ""),
        "personalized_message": message,
    }


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: set GEMINI_API_KEY in your environment (see config/.env.example)")
        sys.exit(1)

    genai.configure(api_key=api_key)

    in_path = os.path.join(os.path.dirname(__file__), "..", "output", "step3_signal_checked.json")
    with open(in_path) as f:
        companies = json.load(f)

    out_path = os.path.join(os.path.dirname(__file__), "..", "output", "step4_final_outreach.json")

    # `results` is the single source of truth for this run, keyed by
    # (company, contact_name). It's seeded from whatever's already on disk,
    # and only ever grows/updates — it is NEVER rebuilt from scratch. This
    # means saving mid-run (or stopping early on a quota wall) can never
    # erase a company's data just because the loop hadn't reached it yet.
    results = {}
    if os.path.exists(out_path):
        with open(out_path) as f:
            for row in json.load(f):
                results[(row["company"], row["contact_name"])] = row

    done_count = sum(1 for r in results.values() if r.get("personalized_message", "").strip())
    if done_count:
        print(f"Resuming: found {done_count} already-completed messages, will skip those.")

    def save():
        with open(out_path, "w") as f:
            json.dump(list(results.values()), f, indent=2)

    # The active model persists across contacts once switched — a previous
    # bug here only used the fallback for the one contact that triggered the
    # switch, then went right back to the exhausted primary model next.
    model_name = GEMINI_MODEL
    model = genai.GenerativeModel(model_name)

    stopped_early = False
    for company in companies:
        for contact in company.get("contacts", []):
            if not contact.get("email"):
                continue

            key = (company["name"], contact["name"])
            existing = results.get(key)
            if existing and existing.get("personalized_message", "").strip():
                continue  # already have a real message for this one, skip

            print(f"  -> writing message for {contact['name']} ({company['name']})...")
            try:
                message = personalize(model, company, contact)
            except DailyQuotaExhausted:
                if model_name == GEMINI_FALLBACK_MODEL:
                    print(f"  !! daily quota exhausted on fallback model too. "
                          f"Stopping here — progress is saved, rest will resume "
                          f"next run (tomorrow, or once quota resets).")
                    results[key] = make_row(company, contact, "")
                    save()
                    stopped_early = True
                    break
                else:
                    print(f"  !! daily quota hit on {model_name}, "
                          f"switching to fallback model {GEMINI_FALLBACK_MODEL} "
                          f"for the rest of this run...")
                    model_name = GEMINI_FALLBACK_MODEL
                    model = genai.GenerativeModel(model_name)
                    try:
                        message = personalize(model, company, contact)
                    except Exception as e:
                        print(f"  !! fallback also failed on {contact['name']}: "
                              f"{type(e).__name__}: {e}")
                        message = ""
            except Exception as e:
                print(f"  !! failed on {contact['name']}: {type(e).__name__}: {e}")
                message = ""

            results[key] = make_row(company, contact, message)
            save()  # always writes the FULL results dict, nothing already-good is ever lost
            time.sleep(13)

        if stopped_early:
            break

    total_done = sum(1 for r in results.values() if r.get("personalized_message", "").strip())
    print(f"\nDone. {total_done} of {len(results)} personalized messages -> {out_path}")


if __name__ == "__main__":
    main()
