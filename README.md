# jev-tern

A small agent that finishes a plain-language task in a visible browser tab. You give it a
goal and a start URL; it clicks, types, selects, scrolls, closes popups, and can click
things drawn on a canvas. It runs on Tern's picture-in-picture WebKit tab, so you watch
every step in your own browser and no headless browser is needed.

Decisions come from TypeSafe's Jev (one request per step: which operation, which target,
is the goal met). Field values are typed by GLM-5.3-Flash. Everything mechanical — page
readiness, scroll positions, image sizing, exact task-text matches — is decided in code,
and the model only receives clean facts.

## Use

```js
import { run } from "./jevTern.mjs";
const r = await run({
  task: "Open today's featured article",
  startUrl: "https://en.wikipedia.org/wiki/Main_Page",
  maxSteps: 12,        // default 14
  maxSeconds: 90,      // default 100
  tabName: "jev-tern", // the reused Tern PiP tab
  allowedDomains: ["en.wikipedia.org"], // optional
  markdown: true,      // optional: return the final page as markdown
});
```

The result carries:

- `status`: `done` | `blocked` | `stuck` | `budget` | `error`
- `goal`: 0–1 probability that every requirement of the task is satisfied
- `steps`: per-step evidence (operation, target, confidence, timings)
- `markdown`: the final page's main content as markdown (only with `markdown: true`)

Sequential calls only; two browser calls on the same tab must not run in parallel.

## What it handles

- Click, type, native select, scroll, and jumps straight to any section heading.
- Popups: shadow DOM is pierced (consent banners become visible buttons), overlays are
  detected mechanically, and dismissing them is a normal click.
- Canvas pages: when a page has almost no DOM, it screenshots the viewport, asks a Box
  question for the right control, and clicks the returned coordinates. Measured 3 px off
  a drawn circle; the native click reaches canvas hit testing.
- Fetch-style tasks: `markdown: true` returns the main content (headings, paragraphs,
  lists, links, tables; 20k cap; navigation and citation markers removed).
- Shortcuts: if the task text names a unique select option or link, code runs it directly
  without asking the model, and never twice in a row. Section jumps take this path only
  for navigation-style tasks, so an answer-seeking task is never dragged to a same-named
  section away from the content that answers it.

Measured results, method, and reproduce commands for every task below: [BENCHMARK.md](BENCHMARK.md).
Rough guide: featured article 2–8 s, site search and open 8–14 s, form fill and submit 13 s,
select 1.3 s, canvas click 2.1 s, section jump 0.9 s, one-hop fetch with markdown back
0.3 s of loop time on top of page load. Each judgment round-trip is 250–400 ms.

## Requires

An OMP-style environment: a `browser` global with Tern tab control (or adapt the tab
calls to another CDP-free bridge), plus `omp token typesafe` and `omp token zai` for the
two keys. Canvas and image questions need TypeSafe's image flag and `jev-1.14.0` or newer.

## Limits

- Top frame only; iframe content is invisible to the snapshot.
- Never logs in and never enters credentials. Login walls end as `blocked`.
- Image questions are preview-grade on TypeSafe's side and may change between releases.
- Each screenshot costs about 4k input tokens; the engine attaches one only when the page
  is DOM-thin, an overlay is present, or two actions in a row changed nothing.

## Licence and credits

MIT. The snapshot and rules text are ports from the MIT-licensed browser-use /
jev-ultrafast projects. Jev and the Box question type are from TypeSafe AI (early
access). Typing uses GLM-5.3-Flash through bigmodel's OpenAI-compatible endpoint.
