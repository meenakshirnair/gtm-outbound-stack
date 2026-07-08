"""
Seed target list for the outbound demo.
ICP: PE-backed, mid-market SaaS companies with a RevOps/GTM function to sell into.
This mirrors InRule's own profile (PE-backed decision automation software), which is
the point: the demo shows the exact kind of company InRule's own GTM team would target.

In a production version this list would itself be Apify-scraped from a source like
Crunchbase/PitchBook company-search results. For the demo, a hand-picked seed list
keeps the run fast and the output easy to talk through on a Loom.
"""

TARGET_COMPANIES = [
    {"name": "InRule Technology", "domain": "inrule.com", "category": "decision automation"},
    {"name": "Definitive Healthcare", "domain": "definitivehc.com", "category": "healthcare data SaaS"},
    {"name": "Smartsheet", "domain": "smartsheet.com", "category": "work management SaaS"},
    {"name": "Egnyte", "domain": "egnyte.com", "category": "content governance SaaS"},
    {"name": "PowerSchool", "domain": "powerschool.com", "category": "edtech SaaS"},
    {"name": "Vena Solutions", "domain": "venasolutions.com", "category": "FP&A SaaS"},
    {"name": "Board International", "domain": "board.com", "category": "decision-making platform"},
    {"name": "Alteryx", "domain": "alteryx.com", "category": "data analytics SaaS"},
    {"name": "Sovos", "domain": "sovos.com", "category": "tax compliance SaaS"},
    {"name": "Ivanti", "domain": "ivanti.com", "category": "IT/security SaaS"},
]
