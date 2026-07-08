# Make.com Scenario: GTM Outbound Pipeline

Make.com is the orchestration layer, the thing that turns 5 separate scripts
into one pipeline that runs on a schedule without you touching it. This is
what "identical architecture to what a GTM team would build" actually means:
each step below is one module in a single Make.com scenario.

## Scenario structure

1. **Trigger**: Scheduled (e.g. daily 8am) or manual "Run once" for the demo.

2. **Module 1 — HTTP: Run Apify Actor**
   - Action: `HTTP > Make a request`
   - Calls `POST https://api.apify.com/v2/acts/apify~website-content-crawler/runs`
   - Body: target company URLs from `target_companies.py` (stored as a Make Data Store)
   - Waits for run completion, pulls dataset via `GET /v2/datasets/{id}/items`

3. **Module 2 — Apollo: HTTP request per company**
   - Action: `HTTP > Make a request`, looped over Module 1's output (Make's
     built-in iterator)
   - Calls Apollo's `mixed_people/search` endpoint per company domain
   - Filters by the RevOps/GTM title list

4. **Module 3 — Webhook to Puppeteer runner**
   - Make doesn't run headless Chrome natively, so this module calls an HTTP
     webhook pointed at a small hosted endpoint (e.g. a Render/Railway service
     wrapping `step3_signal_check.js`) and waits for the JSON response
   - This is the standard pattern for slotting a Node/Puppeteer job into a
     no-code orchestrator

5. **Module 4 — Anthropic: Create a Message**
   - Make has a native Anthropic app; module = `Create a Message`
   - Input: the prompt template from `step4_claude_personalize.py`, with
     company/contact fields mapped in from prior modules
   - Looped per contact

6. **Module 5a — Google Sheets: Add a Row**
   - Native Google Sheets module, one row per contact, same columns as
     `step5_sheet_output.py`

7. **Module 5b — Gmail: Create a Draft**
   - Native Gmail module, `Create a Draft`, populated from the same row

## Why this split (script-first, then Make)

The Python/Node scripts in this repo are the same logic Make would run, built
standalone so you can develop, test, and debug each stage locally before
wiring it into Make (which is much slower to iterate on). For the actual
InRule demo, running the scripts directly and recording that is faster and
more reliable than debugging a live Make scenario on camera. If asked in the
interview how it's productionized, the honest answer is: local scripts for
dev, same calls ported into Make modules for the scheduled, no-code-maintained
production version — which is a completely normal and expected engineering
pattern, not a discrepancy.
