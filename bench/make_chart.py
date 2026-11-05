# Benchmark chart for BENCHMARK.md: median wall time (log) with per-run spread + success rate.
# Usage: uv run --with matplotlib bench/make_chart.py   (writes docs/bench-chart.png)
import json
import random
import statistics
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

random.seed(7)
ROOT = Path(__file__).resolve().parent.parent
rows = json.loads((ROOT / "bench" / "RESULTS.json").read_text())

CONTENDERS = ["playwright-script", "jev-tern", "browser-use"]
LABELS = {"playwright-script": "Playwright script", "jev-tern": "jev-tern", "browser-use": "browser-use"}
COLORS = {"playwright-script": "#9aa0a6", "jev-tern": "#2563eb", "browser-use": "#f59e0b"}
TASKS = [("t1-fetch", "One-hop fetch"), ("t2-portal", "Portal → article"), ("t3-section", "Section jump")]

GRAY = "#6b7280"

def runs(task, c):
    return [r for r in rows if r["task"] == task and r["contender"] == c]

def med(task, c):
    xs = [r["wall_s"] for r in runs(task, c) if r["success"]]
    return statistics.median(xs) if xs else None

fig = plt.figure(figsize=(11.5, 4.6), facecolor="white")
fig.suptitle("Same three live tasks · one machine · one set of keys",
             fontsize=13, fontweight="bold", x=0.02, ha="left", y=0.97)
fig.text(0.02, 0.895, "median wall seconds (log scale, labels) with all runs as dots · 3 runs per task · 2026-11-05",
         fontsize=9, color=GRAY, ha="left")
ax1 = fig.add_axes([0.055, 0.16, 0.60, 0.66])
ax2 = fig.add_axes([0.745, 0.16, 0.225, 0.66])

# ---- Left: grouped bars (median of successful runs) + dots (every run) ----
w = 0.24
for i, c in enumerate(CONTENDERS):
    for t_i, (tid, _) in enumerate(TASKS):
        rs = runs(tid, c)
        m = med(tid, c)
        x = t_i + (i - 1) * w
        if m:
            ax1.bar([x], [m], w, color=COLORS[c], zorder=2)
            top = max([r["wall_s"] for r in rs] + [m])
            ax1.text(x, top * 1.45, f"{m:.1f}s", ha="center", va="bottom",
                     fontsize=9.5, fontweight="bold", color=COLORS[c], zorder=4)
        elif rs:
            ax1.text(x, 0.55, f"0/{len(rs)}", ha="center", va="bottom",
                     fontsize=9, color=COLORS[c], zorder=4)
        for r in rs:
            dx = random.uniform(-w * 0.28, w * 0.28)
            if r["success"]:
                ax1.plot([x + dx], [r["wall_s"]], "o", ms=4.5, mfc="white",
                         mec=COLORS[c], mew=1.4, zorder=3, alpha=0.95)
            else:
                ax1.plot([x + dx], [max(r["wall_s"], 0.5)], "x", ms=6,
                         mec=COLORS[c], mew=1.6, zorder=3)

ax1.set_yscale("log")
ax1.set_ylim(0.4, 300)
ax1.set_yticks([1, 3, 10, 30, 100])
ax1.set_yticklabels(["1", "3", "10", "30", "100"])
ax1.set_xticks(range(len(TASKS)))
ax1.set_xticklabels([n for _, n in TASKS], fontsize=10)
ax1.set_ylabel("wall seconds (log)", fontsize=9.5, color=GRAY)
ax1.tick_params(colors=GRAY, labelsize=9)
ax1.grid(axis="y", which="major", color="#e5e7eb", lw=0.8, zorder=0)
for s in ("top", "right"):
    ax1.spines[s].set_visible(False)
for s in ("left", "bottom"):
    ax1.spines[s].set_color("#d1d5db")
handles = [plt.Rectangle((0, 0), 1, 1, fc=COLORS[c]) for c in CONTENDERS]
ax1.legend(handles, [LABELS[c] for c in CONTENDERS], loc="upper left",
           frameon=False, fontsize=9.5, ncol=1, bbox_to_anchor=(0.0, 1.02))

# ---- Right: success rate with direct labels ----
succ = {c: sum(1 for r in rows if r["contender"] == c and r["success"]) for c in CONTENDERS}
tot = {c: sum(1 for r in rows if r["contender"] == c) for c in CONTENDERS}
order = list(reversed(CONTENDERS))
bars = ax2.barh([LABELS[c] for c in order], [succ[c] / tot[c] * 100 if tot[c] else 0 for c in order],
                height=0.52, color=[COLORS[c] for c in order], zorder=2)
for b, c in zip(bars, order):
    if tot[c]:
        pct = succ[c] / tot[c] * 100
        if pct >= 25:
            ax2.text(pct - 2.5, b.get_y() + b.get_height() / 2, f"{succ[c]}/{tot[c]}",
                     va="center", ha="right", fontsize=10, fontweight="bold", color="white")
        else:
            ax2.text(pct + 2.5, b.get_y() + b.get_height() / 2, f"{succ[c]}/{tot[c]}",
                     va="center", ha="left", fontsize=10, fontweight="bold", color=COLORS[c])
ax2.set_xlim(0, 100)
ax2.set_xticks([0, 50, 100])
ax2.set_xticklabels(["0", "50", "100%"], fontsize=9)
ax2.tick_params(colors=GRAY, labelsize=9.5)
ax2.set_title("task success", fontsize=10.5, color="#374151", pad=8)
ax2.grid(axis="x", color="#e5e7eb", lw=0.8, zorder=0)
for s in ("top", "right"):
    ax2.spines[s].set_visible(False)
for s in ("left", "bottom"):
    ax2.spines[s].set_color("#d1d5db")

out = ROOT / "docs" / "bench-chart.png"
out.parent.mkdir(exist_ok=True)
fig.savefig(out, dpi=150, facecolor="white")
print("wrote", out)
