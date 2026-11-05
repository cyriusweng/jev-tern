import { parseArgs } from "node:util";
import { attachCdpBridge } from "./cdp-bridge.mjs";

const { values, positionals } = parseArgs({
  options: {
    task: { type: "string", short: "t" },
    url: { type: "string", short: "u" },
    headless: { type: "boolean", default: false },
    markdown: { type: "boolean", default: false },
    "max-steps": { type: "string" },
    "max-seconds": { type: "string" },
    tab: { type: "string", default: "jev-tern" },
    cdp: { type: "string" },
    json: { type: "boolean", default: false },
    help: { type: "boolean", short: "h", default: false },
  },
  allowPositionals: true,
});

if (values.help || (!values.task && positionals.length === 0)) {
  console.log(`Usage:
  node run.mjs "<task>" [startUrl] [options]

Options:
  -t, --task <text>        Task instructions
  -u, --url <url>          Starting page URL (default: about:blank)
      --headless           Run browser headlessly
      --markdown           Return extracted markdown of final page
      --max-steps <n>      Step budget (default: 14)
      --max-seconds <n>    Time budget in seconds (default: 100)
      --tab <name>         Tab identifier (default: jev-tern)
      --cdp <url>          Connect via CDP instead of launching Chromium
      --json               Print machine-readable JSON result
  -h, --help               Show this help message
`);
  process.exit(values.help ? 0 : 1);
}

const task = values.task || positionals[0];
const startUrl = values.url || positionals[1] || "about:blank";
const maxSteps = values["max-steps"] ? Number.parseInt(values["max-steps"], 10) : 14;
const maxSeconds = values["max-seconds"] ? Number.parseInt(values["max-seconds"], 10) : 100;
const tabName = values.tab;
const markdown = values.markdown;

let browser = null;
try {
  browser = await attachCdpBridge({
    headless: values.headless,
    cdpUrl: values.cdp,
  });

  const jt = await import("./jevTern.mjs");
  const result = await jt.run({
    task,
    startUrl,
    maxSteps,
    maxSeconds,
    tabName,
    markdown,
  });

  if (values.json) {
    console.log(JSON.stringify(result, null, 2));
  } else {
    console.log(`Status:  ${result.status} (goal: ${result.goal.toFixed(2)})`);
    console.log(`Time:    ${result.elapsed_s.toFixed(2)}s (${result.steps.length} steps)`);
    console.log(`Title:   ${result.finalTitle || "-"}`);
    console.log(`URL:     ${result.finalUrl || "-"}`);
    if (result.error) console.log(`Error:   ${result.error}`);
    if (result.markdown) {
      console.log(`\n--- Markdown (${result.markdown.length} chars) ---`);
      console.log(result.markdown.slice(0, 500) + (result.markdown.length > 500 ? "\n..." : ""));
    }
  }

  process.exitCode = result.status === "done" ? 0 : 1;
} catch (err) {
  console.error("Execution failed:", err.message);
  process.exitCode = 1;
} finally {
  if (browser) {
    await browser.close().catch(() => {});
  }
}
