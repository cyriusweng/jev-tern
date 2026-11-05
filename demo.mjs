import { mkdirSync, readdirSync, rmSync } from "node:fs";
import { attachCdpBridge } from "./cdp-bridge.mjs";

const DIR = "demo-video";
rmSync(DIR, { recursive: true, force: true });
mkdirSync(DIR);

const browser = await attachCdpBridge({
  headless: true,
  recordVideo: { dir: DIR, size: { width: 600, height: 500 } },
});
const tab = await browser.open({ name: "jev-tern-demo", url: "about:blank" });

try {
  const jt = await import("./jevTern.mjs");
  const result = await jt.run({
    task: "In Wikipedia search, find the article about the Rosetta Stone and open it",
    startUrl: "https://en.wikipedia.org/wiki/Main_Page",
    maxSteps: 12,
    maxSeconds: 90,
    tabName: "jev-tern-demo",
  });
  console.log(JSON.stringify({ status: result.status, goal: result.goal, s: result.elapsed_s }));
} finally {
  await new Promise((r) => setTimeout(r, 1500));
  await browser.close().catch(() => {});
}

const webm = readdirSync(DIR).map((f) => `${DIR}/${f}`).pop();
console.log(webm);
