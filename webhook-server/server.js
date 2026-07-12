/**
 * Webhook server for the Puppeteer signal-check step.
 *
 * Why this exists: Make.com can orchestrate HTTP calls but can't run a real
 * headless browser itself. This turns the local step3_signal_check.js logic
 * into a small HTTP service that Make can call as one module in the
 * scenario, same job as before (check a company's careers page for open
 * roles matching my target titles), just reachable over the network instead
 * of run locally.
 *
 * Uses puppeteer-core + @sparticuz/chromium instead of plain puppeteer,
 * because plain puppeteer bundles a full ~300MB Chromium download that
 * regularly fails to build on free hosting tiers (Render/Railway free web
 * services have limited build memory). @sparticuz/chromium is a Chromium
 * binary specifically built small and fast for serverless/limited hosts.
 *
 * Endpoint: POST /check-signal
 * Body: { "name": "InRule Technology", "domain": "inrule.com" }
 * Header: x-webhook-secret: <WEBHOOK_SECRET> (set as an env var on Render)
 * Returns: { name, domain, hiring_signal, matched_keywords, page_load_failed, load_error }
 */

const express = require('express');
const chromium = require('@sparticuz/chromium');
const puppeteer = require('puppeteer-core');

const app = express();
app.use(express.json());

const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET;

const SIGNAL_KEYWORDS = [
  'product analyst', 'technical business analyst', 'business analyst',
  'systems analyst', 'ai/ml', 'machine learning analyst', 'ai analyst',
  'gtm engineer', 'go-to-market engineer', 'revenue operations analyst',
  'business intelligence', 'artificial intelligence analyst', 'gtm', 'go-to-market',
];

app.post('/check-signal', async (req, res) => {
  if (WEBHOOK_SECRET && req.headers['x-webhook-secret'] !== WEBHOOK_SECRET) {
    return res.status(401).json({ error: 'unauthorized' });
  }

  const { name, domain } = req.body || {};
  if (!domain) {
    return res.status(400).json({ error: 'domain is required' });
  }

  let browser;
  try {
    browser = await puppeteer.launch({
      args: chromium.args,
      executablePath: await chromium.executablePath(),
      headless: chromium.headless,
    });

    const page = await browser.newPage();
    const url = `https://${domain}/careers`;
    let signal = false;
    let matchedKeywords = [];

    let pageLoadFailed = false;
    let loadError = null;

    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 40000 });
      // Many careers pages fetch their actual job listings via a separate API
      // call AFTER the page itself loads (React/Next.js style), so a short
      // fixed pause isn't enough — 5s gives that fetch real time to complete.
      await new Promise((r) => setTimeout(r, 5000));

      for (let i = 0; i < 5; i++) {
        await page.evaluate(() => window.scrollBy(0, window.innerHeight));
        await new Promise((r) => setTimeout(r, 800));
      }

      const bodyText = await page.evaluate(() => document.body.innerText.toLowerCase());

      for (const kw of SIGNAL_KEYWORDS) {
        if (bodyText.includes(kw)) {
          signal = true;
          matchedKeywords.push(kw);
        }
      }
    } catch (pageErr) {
      pageLoadFailed = true;
      loadError = pageErr.message;
      console.log(`  careers page fetch failed for ${domain}: ${pageErr.message}`);
    }

    res.json({
      name,
      domain,
      hiring_signal: signal,
      matched_keywords: matchedKeywords,
      page_load_failed: pageLoadFailed,
      load_error: loadError,
    });
  } catch (err) {
    console.error('Signal check failed:', err);
    res.status(500).json({ error: err.message });
  } finally {
    if (browser) await browser.close();
  }
});

app.get('/', (req, res) => {
  res.json({ status: 'ok', service: 'signal-check-webhook' });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Signal-check webhook listening on port ${PORT}`);
});
