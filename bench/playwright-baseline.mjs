// Deterministic Playwright baseline for the three benchmark tasks.
// Same pages, same success criteria as the agent runs; a hand-written script per task.
// Usage: node bench/playwright-baseline.mjs   (appends to bench/RESULTS.json)
import { chromium } from "playwright";
import { readFileSync, writeFileSync, existsSync } from "node:fs";

const RESULTS = new URL("./RESULTS.json", import.meta.url).pathname;
const results = existsSync(RESULTS) ? JSON.parse(readFileSync(RESULTS, "utf8")) : [];
const push = r => { results.push(r); writeFileSync(RESULTS, JSON.stringify(results, null, 1)); };

const browser = await chromium.launch();

async function t1() { // one-hop fetch: article lead names the artist
  const t0 = Date.now(); const page = await browser.newPage();
  await page.goto("https://en.wikipedia.org/wiki/Mona_Lisa", { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("load");
  const ok = (await page.evaluate(() => document.body.innerText)).includes("Leonardo");
  return { wall_s: +((Date.now() - t0) / 1000).toFixed(1), steps: 1, success: ok };
}
async function t2() { // portal: Main Page featured-article box -> the day's article
  const t0 = Date.now(); const page = await browser.newPage();
  await page.goto("https://en.wikipedia.org/wiki/Main_Page", { waitUntil: "domcontentloaded" });
  await page.click("#mp-tfa b a");
  await page.waitForLoadState("load");
  const url = page.url();
  const ok = /\/wiki\/[^:]+$/.test(new URL(url).pathname) && !url.includes("Today");
  return { wall_s: +((Date.now() - t0) / 1000).toFixed(1), steps: 2, success: ok };
}
async function t3() { // section jump: bring References heading into view
  const t0 = Date.now(); const page = await browser.newPage();
  await page.goto("https://en.wikipedia.org/wiki/G%C3%B6del%27s_incompleteness_theorems", { waitUntil: "domcontentloaded" });
  await page.evaluate(() => document.querySelector("#References, span#References")?.scrollIntoView());
  const top = await page.evaluate(() => { const el = document.querySelector("#References, span#References"); const r = el?.getBoundingClientRect(); return r ? r.top : -1; });
  return { wall_s: +((Date.now() - t0) / 1000).toFixed(1), steps: 2, success: top >= 0 && top < innerHeightSafe() };
  function innerHeightSafe() { return 800; }
}

for (const [id, fn] of [["t1-fetch", t1], ["t2-portal", t2], ["t3-section", t3]])
  for (let i = 0; i < 3; i++) {
    const r = await fn();
    push({ task: id, contender: "playwright-script", run: i + 1, ...r, note: "hand-written deterministic script" });
    console.log(id, "run", i + 1, JSON.stringify(r));
  }

await browser.close();
