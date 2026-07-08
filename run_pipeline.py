"""
Runs the full pipeline in order: Apify -> Apollo -> [Puppeteer runs separately,
it's Node] -> Claude -> Sheets + Gmail.

Usage:
    python run_pipeline.py                  # runs Apify + Apollo + Claude + Sheets + Gmail
    python run_pipeline.py --skip-gmail      # skip Gmail draft creation
    python run_pipeline.py --skip-sheet      # skip Google Sheet push

Before running this, run the Puppeteer signal check separately:
    cd puppeteer && npm install && node step3_signal_check.js

That's a deliberate split, not an oversight: Puppeteer is Node, everything
else here is Python. In the Make.com version (see make_scenario_blueprint.md)
this seam disappears because Make orchestrates both regardless of language.
"""

import argparse
import subprocess
import sys
import os

STEPS_DIR = os.path.join(os.path.dirname(__file__), "src")


def run_step(script_name: str):
    path = os.path.join(STEPS_DIR, script_name)
    print(f"\n=== Running {script_name} ===")
    result = subprocess.run([sys.executable, path])
    if result.returncode != 0:
        print(f"!! {script_name} failed, stopping pipeline.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-gmail", action="store_true")
    parser.add_argument("--skip-sheet", action="store_true")
    args = parser.parse_args()

    run_step("step1_apify_scrape.py")
    run_step("step2_apollo_enrich.py")

    print("\n>>> Now run the Puppeteer signal check before continuing:")
    print(">>>   cd puppeteer && node step3_signal_check.js")
    input(">>> Press Enter once that's finished to continue with Claude personalization...")

    run_step("step4_claude_personalize.py")

    if not args.skip_sheet:
        run_step("step5_sheet_output.py")
    if not args.skip_gmail:
        run_step("step5_gmail_drafts.py")

    print("\nPipeline complete. Check output/step4_final_outreach.json and your Sheet/Gmail drafts.")


if __name__ == "__main__":
    main()
