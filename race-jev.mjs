// One recorded jev-tern run, for the race demo video.
// The engine drives its own chromium (CDP port 9334); a second connection
// screencasts its pages with unix-timestamped frames into race-left/frames/.
import { mkdirSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { attachCdpBridge } from "./cdp-bridge.mjs";

let pw;
try {
  pw = await import("playwright");
} catch {
  pw = await import("./bench/node_modules/playwright/index.mjs");
}

rmSync("race-left", { recursive: true, force: true });
mkdirSync("race-left/frames", { recursive: true });

const browser = await attachCdpBridge({
  viewport: { width: 1200, height: 1000 },
  launchArgs: ["--remote-debugging-port=9334"],
});

const conn = await pw.chromium.connectOverCDP("http://127.0.0.1:9334");
const manifest = [];
let frameNo = 0;
const t0 = Date.now();
const attached = new Set();

async function attachContext(ctx) {
  for (const page of ctx.pages()) {
    if (attached.has(page)) continue;
    attached.add(page);
    const s = await ctx.newCDPSession(page);
    s.on("Page.screencastFrame", (ev) => {
      const ts = Date.now();
      const name = `f01_${String(ts - t0).padStart(7, "0")}.jpg`;
      writeFileSync(`race-left/frames/${name}`, Buffer.from(ev.data, "base64"));
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

const jt = await import("./jevTern.mjs");
const runStart = Date.now();
const r = await jt.run({
  task: "Search Wikipedia for the Rosetta Stone, open the article, and jump to the \"Rediscovery\" section",
  startUrl: "https://en.wikipedia.org/wiki/Main_Page",
  maxSteps: 14,
  maxSeconds: 90,
  tabName: "race",
  allowedDomains: ["en.wikipedia.org"],
});
const runEnd = Date.now();

await new Promise((res) => setTimeout(res, 1200));
clearInterval(watcher);
writeFileSync("race-left/timing.json", JSON.stringify({ t0, runStart, runEnd }));
writeFileSync("race-left/frames/manifest.txt", manifest.join("\n") + "\n");
await conn.close().catch(() => {});
await browser.close().catch(() => {});

console.log(JSON.stringify({
  status: r.status, goal: r.goal, s: r.elapsed_s, url: r.finalUrl,
  frames: manifest.length,
}));
