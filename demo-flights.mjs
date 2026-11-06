// The hero demo: one Google Flights task, recorded with a live checklist trace.
// Frames + manifest land in flights-video/frames; checklist and timings in
// flights-video/trace.json. Run: node demo-flights.mjs
import { mkdirSync, writeFileSync } from "node:fs";
import { attachCdpBridge } from "./cdp-bridge.mjs";

let pw;
try {
  pw = await import("playwright");
} catch {
  pw = await import("./bench/node_modules/playwright/index.mjs");
}

mkdirSync("flights-video/frames", { recursive: true });

const browser = await attachCdpBridge({
  headless: true,
  viewport: { width: 1200, height: 1000 },
  launchArgs: ["--remote-debugging-port=9335"],
});

// Checklist observes the real page: whenever the engine reads the page
// signature, the field values in the result mark requirements as met.
const checks = [
  { label: "Zürich", test: (s) => /z(ü|u)rich|zrh/i.test(s) },
  { label: "London", test: (s) => /london|lhr|lcy/i.test(s) },
  { label: "15 December", test: (s) => /dec|december/i.test(s) && /15|15 december/i.test(s) },
  { label: "Results visible", test: () => false },
];
const checkState = checks.map(() => 0); // 0 pending, else ts_ms

const t0 = Date.now();
const conn = await pw.chromium.connectOverCDP("http://127.0.0.1:9335");
const manifest = [];
const attached = new Set();

async function attachContext(ctx) {
  for (const page of ctx.pages()) {
    if (attached.has(page)) continue;
    attached.add(page);
    const s = await ctx.newCDPSession(page);
    s.on("Page.screencastFrame", (ev) => {
      const ts = Date.now();
      const name = `f01_${String(ts - t0).padStart(7, "0")}.jpg`;
      writeFileSync(`flights-video/frames/${name}`, Buffer.from(ev.data, "base64"));
      manifest.push(`${(ts / 1000).toFixed(3)} ${name}`);
      s.send("Page.screencastFrameAck", { sessionId: ev.sessionId }).catch(() => {});
    });
    await s.send("Page.startScreencast",
      { format: "jpeg", quality: 92, maxWidth: 1200, maxHeight: 1000 });
  }
}
for (const ctx of conn.contexts()) await attachContext(ctx);
const watcher = setInterval(async () => {
  for (const ctx of conn.contexts()) await attachContext(ctx).catch(() => {});
}, 500);

// Field observation through the engine's own page-signature reads.
const tab = await browser.open({ name: "flights-demo", url: "about:blank" });
const origEvaluate = tab.evaluate.bind(tab);
tab.evaluate = async (js) => {
  const r = await origEvaluate(js);
  if (typeof r === "string" && r.includes("|") && r.includes("¶")) {
    const now = Date.now();
    checks.forEach((c, i) => {
      if (!checkState[i] && i < 4 && c.test(r)) checkState[i] = now - t0;
    });
  }
  return r;
};

const jt = await import("./jevTern.mjs");
const runStart = Date.now();
const r = await jt.run({
  task: "Find one-way flights from Zurich to London on 15 December 2026 for one adult in economy. Stop when matching flight options are visible.",
  startUrl: "https://www.google.com/travel/flights?hl=en",
  maxSteps: 16,
  maxSeconds: 120,
  tabName: "flights-demo",
  allowedDomains: ["google.com"],
});
const runEnd = Date.now();

// Independent verification of the outcome, after the run.
let verify = {};
try {
  verify = await origEvaluate(`(() => {
    const t = document.body.innerText.slice(0, 4000);
    const url = location.href;
    return {
      url_ok: /travel\\/flights/.test(url),
      zurich: /z(ü|u)rich|ZRH/i.test(t),
      london: /london|LHR|LCY/i.test(t),
      date: /15|Dec/i.test(t),
      results: /(departing|arrival|nonstop|stops)/i.test(t),
      title: document.title.slice(0, 60),
    };
  })()`);
} catch {}
if (verify.zurich && verify.london && verify.date && verify.results) {
  checkState[checks.length - 1] = runEnd - t0;
}

await new Promise((res) => setTimeout(res, 1500));
clearInterval(watcher);
writeFileSync("flights-video/frames/manifest.txt", manifest.join("\n") + "\n");

const decideMs = r.steps.filter((s) => Number.isFinite(s.decide_ms)).map((s) => s.decide_ms).sort((a, b) => a - b);
const trace = {
  runStartOffset: runStart - t0,
  runEndOffset: runEnd - t0,
  elapsed_s: r.elapsed_s,
  status: r.status,
  goal: r.goal,
  url: r.finalUrl,
  steps: r.steps.length,
  actions: r.steps.filter((s) => s.operation && s.operation !== "WAIT").length,
  median_decide_ms: decideMs.length ? decideMs[Math.floor(decideMs.length / 2)] : null,
  checks: checks.map((c, i) => ({ label: c.label, at_ms: checkState[i] || null })),
  verify,
  usage: r.usage,
};
writeFileSync("flights-video/trace.json", JSON.stringify(trace, null, 1));

await conn.close().catch(() => {});
await browser.close().catch(() => {});
console.log(JSON.stringify(trace));
