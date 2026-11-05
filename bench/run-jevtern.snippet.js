// Reproducibility snippet for the jev-tern side of the benchmark.
// Runs inside an OMP-style JS eval (the `browser` global and the two keys live there):
//   1. node bench/playwright-baseline.mjs
//   2. bench/.venv/bin/python bench/browser-use-task.py
//   3. paste this file's body into the eval
//   4. uv run --with matplotlib bench/make_chart.py
import { readFileSync, writeFileSync } from "node:fs";

const jt = await import("/path/to/jevTern.mjs");
const R = "/path/to/jev-tern/bench/RESULTS.json";

const TASKS = {
  "t1-fetch": { task: "Open the Wikipedia article about the Mona Lisa and confirm who painted it",
                startUrl: "https://en.wikipedia.org/wiki/Mona_Lisa" },
  "t2-portal": { task: "Open today's featured article",
                 startUrl: "https://en.wikipedia.org/wiki/Main_Page" },
  "t3-section": { task: "Bring the 'References' section heading of this article into view",
                  startUrl: "https://en.wikipedia.org/wiki/G%C3%B6del%27s_incompleteness_theorems" },
};

let rows = JSON.parse(readFileSync(R, "utf8"));
rows = rows.filter(r => r.contender !== "jev-tern");
for (const [id, spec] of Object.entries(TASKS)) {
  for (let run = 1; run <= 3; run++) {
    const t0 = Date.now();
    const r = await jt.run({ ...spec, maxSteps: 12, maxSeconds: 90, tabName: "jev-tern-bench", markdown: true });
    // t2 is verified externally by URL, the same check browser-use gets:
    // an article page, with the archive page and Main Page counted as misses.
    let ok = r.status === "done";
    if (id === "t2-portal") {
      const url = r.finalUrl || "";
      const tail = url.split("/wiki/").pop() || "";
      ok = ok && url.includes("/wiki/") && !tail.includes(":")
           && !url.includes("Today") && !url.includes("Main_Page");
    }
    rows.push({ task: id, contender: "jev-tern", run, wall_s: +((Date.now() - t0) / 1000).toFixed(1),
                steps: r.steps.length, success: ok, note: `status=${r.status} goal=${r.goal}` });
    writeFileSync(R, JSON.stringify(rows, null, 1));
    console.log(id, "run", run, r.status, r.elapsed_s + "s loop");
  }
}
