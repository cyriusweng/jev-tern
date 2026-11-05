# Benchmark

Three live Wikipedia tasks, three contenders, three runs each, one machine, one set of API
keys. Every figure below is a measured run; medians are over successful runs and say so.

![Benchmark chart](docs/bench-chart.png)

## Conclusions

1. **Speed: 10–33× over browser-use, at zero measured success cost.** Wall-time medians —
   one-hop fetch 2.9 s vs 28.9 s (**10.0×**), portal search 9.7 s vs 115.5 s (**11.9×**),
   section jump 4.0 s vs 131.5 s (**32.9×**); geometric mean **≈16×** across the suite.
2. **Success was identical: 9/9 for both agents and 9/9 for the script.** Every run of
   every contender met its task criterion; the speed gap carried no success penalty here.
3. **The hand-written script set the floor: 1.4 / 1.6 / 0.6 s medians**, 2.1–6.7× under
   jev-tern. Plain-language tasks cost that margin over a bespoke script per task.

## Contenders

| Contender | What it is | Brain |
|---|---|---|
| **jev-tern** (this repo) | agent loop on Tern's picture-in-picture WebKit tab | TypeSafe Jev `jev-1.14.0` judges each step; GLM-5.3-Flash types values |
| [browser-use](https://github.com/browser-use/browser-use) v0.11.13 | agent loop on headless Playwright Chromium | GLM-5.3 via bigmodel, same key family |
| Playwright script | hand-written deterministic script per task | plain code |

Fairness notes: browser-use ran with the strongest model available on the same bigmodel
key (GLM-5.3). Its usual OpenAI/Anthropic models need a different key and stayed out of
this comparison. jev-tern kept its own judge (TypeSafe Jev) because that is the engine
under test. The Playwright script is the floor case: the fastest possible run, at the cost
of a human writing each task by hand.

## Tasks

| id | task | success criterion |
|---|---|---|
| t1-fetch | open the Mona Lisa article, confirm the artist | article open, artist name present |
| t2-portal | from the Main Page, open today's featured article | final page is the day's article (the archive page counts as a miss) |
| t3-section | bring the References heading into view | heading visible in the viewport |

## Results

| Task (median wall, range) | jev-tern | browser-use | Playwright script |
|---|---|---|---|
| t1-fetch | **2.9 s** (2.4–4.1) | 28.9 s (28.8–33.3) | 1.4 s (1.4–1.9) |
| t2-portal | **9.7 s** (9.6–10.4) | 115.5 s (40.5–154.1) | 1.6 s (1.6–1.8) |
| t3-section | **4.0 s** (3.1–5.7) | 131.5 s (86.7–202.1) | 0.6 s (0.6–0.7) |
| success | **9/9** | 9/9 | 9/9 |

Raw rows: [`bench/RESULTS.json`](bench/RESULTS.json).

## Environment and method

- Apple silicon macOS. jev-tern on Tern's picture-in-picture WebKit; browser-use and the
  script on Playwright Chromium 156 (build 1248), headless.

- Wall time covers the whole task (jev-tern's loop starts after its fixed ~1.6 s load
  wait; both are included in wall time).
- Success for agent runs is the engine's own `done` status; for browser-use, its final
  result and page history; for the script, the criterion checked in code.
- Judgment round-trip inside jev-tern runs: 250–400 ms per step. An 8-step run consumed
  44,371 input / 4,393 output tokens (≈5.5 k in / 550 out per step, snapshot included).

## Reproduce

```bash
cd bench
npm install                                  # playwright for the baseline
node playwright-baseline.mjs                 # 9 rows
uv venv && uv pip install "browser-use==0.11.13" "playwright==1.64.*"
.venv/bin/python browser-use-task.py         # 9 rows
# then run the jev-tern side inside an OMP eval: bench/run-jevtern.snippet.js
uv run --with matplotlib make_chart.py       # writes docs/bench-chart.png
```

Set `BU_BROWSER_PATH` if browser-use cannot find your Chromium; `BU_MODEL` and
`BU_BASE_URL` override its brain.

## Defects these runs exposed in jev-tern (and their fixes)

1. **Restored scroll offset.** Reusing the tab restored the previous scroll position, so
   an answer task could start mid-article and burn its budget scrolling back. Fix: every
   task now starts from a fresh top-of-page viewport.
2. **Dead scroll options.** At the page top, `scroll_up` stayed on offer and was picked
   seven times in a row. Fix: directions that cannot move are removed before the judge
   sees the action list.
3. **Section shortcut on answer tasks.** A task mentioning the page title was dragged to
   a same-named section away from the lead that answered it. Fix: section shortcuts fire
   only for navigation-style tasks ("section", "heading", "跳到", …).
