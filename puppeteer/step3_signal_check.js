/**
 * STEP 3 — PUPPETEER: intent-signal check.
 *
 * Job: Apify's Website Content Crawler is great at public marketing pages,
 * but it can't handle pages that need real interaction — scrolling, clicking
 * "load more", or content injected only after a specific JS event fires
 * (common on company careers boards built on Greenhouse/Lever widgets that
 * lazy-load listings on scroll). Puppeteer gives us a real, scriptable browser
 * to handle that class of page.
 *
 * This is personal job-search outreach, not sales prospecting: here we load
 * each company's careers page, scroll to trigger lazy-loaded job listings,
 * and check whether they're actively hiring for roles matching my actual
 * target titles (Product Analyst, Technical BA, AI/ML BA, Systems Analyst,
 * GTM Engineer). A company with an open, relevant role is a much stronger
 * reason to reach out than one where I'd be cold-emailing into a vacuum.
 *
 * Run: node step3_signal_check.js
 * Requires: npm install puppeteer
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const SIGNAL_KEYWORDS = [
  'product analyst', 'technical business analyst', 'business analyst',
  'systems analyst', 'ai/ml', 'machine learning analyst', 'ai analyst',
  'gtm engineer', 'go-to-market engineer', 'revenue operations analyst',
];

async function checkSignal(browser, company) {
  const page = await browser.newPage();
  const url = `https://${company.domain}/careers`;
  let signal = false;
  let matchedTitles = [];

  try {
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 20000 });

    // scroll a few times to trigger lazy-loaded job boards
    for (let i = 0; i < 3; i++) {
      await page.evaluate(() => window.scrollBy(0, window.innerHeight));
      await new Promise((r) => setTimeout(r, 800));
    }

    const bodyText = await page.evaluate(() => document.body.innerText.toLowerCase());

    for (const kw of SIGNAL_KEYWORDS) {
      if (bodyText.includes(kw)) {
        signal = true;
        matchedTitles.push(kw);
      }
    }
  } catch (err) {
    console.log(`  !! failed on ${company.name}: ${err.message}`);
  } finally {
    await page.close();
  }

  return { ...company, hiring_signal: signal, matched_keywords: matchedTitles };
}

async function main() {
  const inPath = path.join(__dirname, '..', 'output', 'step2_enriched_contacts.json');
  const outPath = path.join(__dirname, '..', 'output', 'step3_signal_checked.json');

  const companies = JSON.parse(fs.readFileSync(inPath, 'utf-8'));
  const browser = await puppeteer.launch({ headless: 'new' });

  const results = [];
  for (const company of companies) {
    console.log(`  -> checking hiring signal: ${company.name}...`);
    results.push(await checkSignal(browser, company));
  }

  await browser.close();
  fs.writeFileSync(outPath, JSON.stringify(results, null, 2));

  const withSignal = results.filter((r) => r.hiring_signal).length;
  console.log(`\nDone. ${withSignal}/${results.length} companies show an open role matching my target titles -> ${outPath}`);
}

main();