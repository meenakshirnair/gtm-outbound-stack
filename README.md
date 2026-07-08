# GTM Outbound Stack

An automated outbound pipeline: Apify (company discovery) → Apollo (contact
enrichment) → Puppeteer (hiring-signal check) → Gemini API (message
personalization) → Google Sheets + Gmail (output).

ICP for this demo: PE-backed, mid-market SaaS companies with a RevOps/GTM
function — the same category of company InRule itself is.

## Why this architecture

Two tools do discovery/scraping (Apify, Puppeteer) and one does data
enrichment (Apollo) because that's the real division of labor in outbound
tooling: scrapers are good at reading pages, data providers are good at
verified contact info, and no single tool does both well. Gemini turns the
combined data into something a rep could actually send. Make.com is the
scheduler/glue that would run this on autopilot in production — see
`make_scenario_blueprint.md` for how the same five steps map onto Make
modules.

## Setup

1. `pip install -r requirements.txt --break-system-packages`
2. `cd puppeteer && npm install`
3. Copy `config/.env.example` to `.env` and fill in your real keys:
   - `APIFY_TOKEN` — https://console.apify.com/account/integrations
   - `APOLLO_API_KEY` — https://app.apollo.io/#/settings/integrations/api
   - `GEMINI_API_KEY` — https://aistudio.google.com/apikey
4. For the Google Sheet output: create a Google Cloud service account with
   Sheets API enabled, download the JSON key, set
   `GOOGLE_SERVICE_ACCOUNT_JSON` to its path, and share your target Sheet
   with the service account's email.
5. For Gmail drafts: create an OAuth client in Google Cloud Console (Desktop
   app type), download as `config/credentials.json`. First run opens a
   browser to authorize.
6. Load your `.env`: `export $(cat .env | xargs)` (or use `python-dotenv` if
   you prefer, not currently wired in).

## Run

```bash
python run_pipeline.py
```

This runs Apify → Apollo, pauses for you to run the Puppeteer step
separately (`cd puppeteer && node step3_signal_check.js`), then continues
with Gemini → Sheets → Gmail.

Run stages individually while developing:

```bash
python src/step1_apify_scrape.py
python src/step2_apollo_enrich.py
node puppeteer/step3_signal_check.js
python src/step4_gemini_personalize.py
python src/step5_sheet_output.py
python src/step5_gmail_drafts.py
```

Each stage reads the previous stage's JSON from `output/` and writes its own,
so you can inspect the data at every handoff — useful both for debugging and
for showing the pipeline's intermediate state on the Loom.

## Before recording the Loom

- Run the full pipeline once end to end with your real keys, on the seed
  list in `config/target_companies.py` (edit the list if you want different
  companies).
- Check `output/step4_final_outreach.json` looks right and the Sheet /ok
  Gmail drafts populated.
- Walk through it in the order a GTM engineer would explain it: discovery →
  enrichment → signal → personalization → delivery. That mirrors exactly what
  you told Rachel, so the narrative and the tool are now the same thing.
