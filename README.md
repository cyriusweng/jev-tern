<div align="center">

<img src="docs/logo.svg" alt="jev-tern" width="420">

**The browser agent born inside [OMP](https://github.com/cyriusweng) + Tern.**

Plain-language tasks, finished in a browser tab you can watch the whole time.

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/cyriusweng/jev-tern.svg)](https://github.com/cyriusweng/jev-tern/stargazers)
![Single file](https://img.shields.io/badge/engine-single%20file-2563eb.svg)

[Benchmark](BENCHMARK.md) · [Quickstart](#quickstart-omp--tern) · [Running it elsewhere](#running-it-elsewhere) · [Credits](#licence-and-credits)

</div>

---

On the same three live tasks, same machine and API keys, three runs per task: jev-tern
finished **18× faster** than [browser-use](https://github.com/browser-use/browser-use) on
a one-hop fetch (1.6 s vs 28.9 s), **34×** on a portal search (3.4 s vs 115.5 s) and
**73×** on a section jump (1.8 s vs 131.5 s) — **9/9 task success** for both agents, with
jev-tern's portal runs verified externally by URL. A hand-written Playwright script set
the speed floor at 0.6–1.6 s per task — it knows each page's DOM in advance, while
jev-tern reads every page for the first time and takes plain language. Full method, raw
results, and chart: **[BENCHMARK.md](BENCHMARK.md)**.

![Benchmark chart](docs/bench-chart.png)

## Born inside OMP + Tern

jev-tern was designed for the OMP + Tern stack, and that is where it lives: it drives
Tern's picture-in-picture WebKit tab (the one you already watch), reads its two keys via
`omp token`, and ships as one ES module you import from an eval. One Jev request judges
each step (250–400 ms); GLM-5.3-Flash types field values; everything mechanical — page
readiness, scroll math, exact task-text matches, image sizing — runs in code, so the judge
only ever sees clean facts.

## Quickstart (OMP + Tern)

```js
const jt = await import("/path/to/jevTern.mjs");
const r = await jt.run({
  task: "Open today's featured article",
  startUrl: "https://en.wikipedia.org/wiki/Main_Page",
  maxSteps: 12,        // default 14
  maxSeconds: 90,      // default 100
  tabName: "jev-tern", // the reused Tern PiP tab
  allowedDomains: ["en.wikipedia.org"], // optional
  markdown: true,      // optional: final page main content back as markdown
});
```

The result carries `status` (`done | blocked | stuck | budget | error`), `goal`
(0–1 probability every requirement is met), per-step evidence in `steps`, and `markdown`
when asked for. Keep two runs on one tab out of `Promise.all`; calls on one tab are
sequential.

## Running it elsewhere

The engine touches the browser only through a small bridge surface. Implement these six
calls on your stack and the rest of the file runs as-is:

| Bridge call | Used for |
|---|---|
| `browser.open({name, url, wait_until})` | open or reuse a tab, returns the tab handle |
| `tab.evaluate(js)` | run JS in the page, get a JSON value back (snapshot, actions, markdown) |
| `tab.clickAt(x, y)` | native click at viewport coordinates (the canvas path) |
| `tab.title()` | watch navigation settle between steps |
| `tab.allowedDomains([…])` | optional domain guard |
| `tab.run(async ({page}) => …)` | full page access, used only for screenshots |

You also need Node ≥ 18 and two API keys — a TypeSafe Jev key and a bigmodel key — read at
runtime from `omp token` (override with `OMP_BIN` if your binary lives elsewhere). Point
`OMP` at your token source or adapt `token()`; everything else is bridge-agnostic.

## What it handles

- Click, type, select, scroll, and straight jumps to section headings; a task naming a
  section in quotes jumps directly when the DOM holds exactly one such heading, then
  hands the measured geometry to the judge as code-verified ground truth.
- Popups: shadow DOM is pierced (consent banners become ordinary buttons), overlays are
  detected mechanically, dismissing them is a normal click.
- Canvas pages: a page with almost nothing in the DOM gets a viewport screenshot, a Box
  question finds the right control, and the returned coordinates are clicked natively —
  measured 3 px off a drawn circle.
- Fetch-style tasks: `markdown: true` returns the final page's main content as markdown
  (headings, paragraphs, lists, links, tables; 20k cap; navigation and citation noise
  removed).
- Shortcuts: a task naming a unique select option or link executes in code without a model
  round, and never twice in a row; shortcuts wait for one judgment step on a freshly
  navigated page.
- Recovery: a GO_BACK control appears whenever a previous distinct page exists, so a
  wrong navigation costs one step.
- Confidence floors: a DONE needs the operation choice, the goal Noul at 0.8+, and the
  judge's own confidence at 0.6+; an action picked below 0.55 attaches a viewport
  screenshot to the next judgment.
- Every task starts from a fresh top-of-page viewport, and scroll directions that cannot
  move are withheld from the judge.
- Honest outcomes: `stuck` and `blocked` come back as they are, with the evidence that
  produced them.

## Requires

An OMP-style environment (a `browser` global with the tab bridge above), `omp token
typesafe` and `omp token zai` for the two keys, and `jev-1.14.0` or newer for Box/image
questions.

## Limits

- The snapshot reads the top frame; iframe content stays out of view.
- Logged-out by design: login walls end as `blocked` with the wall described.
- Image questions follow TypeSafe's preview-grade pipeline and may shift between releases.
- Each screenshot costs about 4k input tokens; the engine attaches one only when pixels
  add signal: DOM-thin pages, overlays, or two actions in a row that changed nothing.

## Licence and credits

MIT. The snapshot and rules text are ports from the MIT-licensed browser-use /
jev-ultrafast projects. Jev and the Box question type are from TypeSafe AI (early access).
Field values are typed by GLM-5.3-Flash through bigmodel's OpenAI-compatible endpoint.
