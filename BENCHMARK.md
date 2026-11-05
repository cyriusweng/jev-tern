# Benchmark

Every number below was measured on live pages, single runs, on the machine that built the
engine. Nothing is averaged away or cherry-picked: where a run exposed a defect, the defect
and its fix are listed at the bottom.

## Environment

- Apple silicon macOS, Tern picture-in-picture browser (WKWebView, no CDP)
- Judgments: TypeSafe systemone, `jev-1.14.0` (one request per step)
- Field typing: GLM-5.3-Flash, bigmodel OpenAI-compatible endpoint
- Date of runs: 2026-11-05

## Method

`loop s` is the agent loop after the page is ready (the engine waits a fixed ~1.6 s for
load before the first step). `wall s` adds that wait. Statuses are the engine's own:
`done` only when the goal judgment crosses threshold; a page that merely loaded never
counts as done.

## Results

| Task | Steps | Loop s | Status | Notes |
|---|---|---|---|---|
| One-hop fetch + markdown back | 1 | 0.3 | done 0.98 | 20k chars returned, answer present |
| Portal search + open (featured article) | 2–5 | 2–8 | done 0.92 | live-site variance: some runs click the archive page and end `stuck` honestly |
| Same + `markdown: true` | 3 | 5.4 | done | 7 section headings extracted |
| Section jump, target off-screen | 8 | 3.7 | done 0.91 | scrolls until the heading becomes a jump target |
| Section jump, target on-screen | 1 | 0.9 | done | deterministic shortcut, no model round |
| Native select | 1–2 | 1.3 | done | option named in the task text |
| Form fill + submit (five fields) | ~10 | 13 | done | values typed by GLM-5.3-Flash |
| Site search + open (multi-hop) | 8–12 | 8–14 | done | search box → results → open item |
| Canvas click (Box question) | 2 | 2.1 | done | 3 px off the drawn target |

Judgment round-trip latency observed inside runs: 250–400 ms per step.

## Reproduce

Run each snippet in an OMP-style JS eval (a `browser` global plus the two keys; see
README "Requires"):

```js
const jt = await import("/path/to/jevTern.mjs");

// One-hop fetch + markdown
await jt.run({ task: "Open the Wikipedia article about the Mona Lisa and confirm who painted it",
  startUrl: "https://en.wikipedia.org/wiki/Mona_Lisa", markdown: true });

// Portal search + open
await jt.run({ task: "Open today's featured article",
  startUrl: "https://en.wikipedia.org/wiki/Main_Page" });

// Section jump, off-screen target
await jt.run({ task: "Bring the 'References' section heading of this article into view",
  startUrl: "https://en.wikipedia.org/wiki/G%C3%B6del%27s_incompleteness_theorems" });
```

Form and select tasks were measured on private demo pages; use any plain five-field form
and a `<select>` whose option text the task names.

## Token use

An 8-step run on a long article consumed 44,371 input / 4,393 output tokens — about
5.5 k in / 550 out per step, snapshot included. Screenshots (~4 k input tokens each) are
attached only when the page is DOM-thin, an overlay is present, or two actions in a row
changed nothing.

## Context

On the same machine this week, the third-party `jev_navigate` MCP tool (a headless
fetcher) took 5.07 s wall on its own demo task. Indicative only: different task and
pipeline, same machine and keys.

## Defects found by these runs (and fixed)

1. **Restored scroll offset.** Reusing the tab restored the previous scroll position, so
   an answer task could start mid-article and burn its budget scrolling back. Fix: every
   task now starts from a fresh top-of-page viewport.
2. **Dead scroll options.** At the page top, `scroll_up` was still offered and was picked
   seven times in a row. Fix: directions that cannot move are removed before the judge
   sees the action list.
3. **Section shortcut on answer tasks.** A task mentioning the page title was dragged to
   a same-named section away from the lead that answered it. Fix: section shortcuts fire
   only for navigation-style tasks ("section", "heading", "跳到", …).
