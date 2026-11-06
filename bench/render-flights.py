# Render the hero demo video: the recorded Google Flights run inside a HUD
# frame (headline, live stopwatch, checklist from trace.json, stats, progress).
# Usage: bench/.venv/bin/python bench/render-flights.py flights-video
import json, math, sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

d = Path(sys.argv[1])
trace = json.loads((d / "trace.json").read_text())
rows = [ln.split() for ln in (d / "frames" / "manifest.txt").read_text().splitlines() if ln.strip()]
frames = {float(ts): name for ts, name in rows}
times = sorted(frames)

W, H = 1920, 1080
FPS = 25
t0_wall = times[0]
END = trace["runEndOffset"] / 1000 + 1.6
N = math.ceil(END * FPS)

SF = "/System/Library/Fonts/SFNS.ttf"
MENLO = "/System/Library/Fonts/Menlo.ttc"
f_head = ImageFont.truetype(SF, 74)
f_sub = ImageFont.truetype(SF, 30)
f_brand = ImageFont.truetype(MENLO, 30)
f_badge = ImageFont.truetype(MENLO, 26)
f_clock = ImageFont.truetype(MENLO, 110)
f_label = ImageFont.truetype(MENLO, 24)
f_item = ImageFont.truetype(MENLO, 34)
f_stat = ImageFont.truetype(MENLO, 46)
f_statlab = ImageFont.truetype(MENLO, 22)
f_foot = ImageFont.truetype(MENLO, 24)

GREEN = (74, 222, 128)
GREY = (156, 163, 175)
WHITE = (243, 244, 246)
DIM = (107, 114, 128)

BX, BY, BW, BH = 56, 152, 1008, 840          # browser window (1200x1000 scaled 0.84)
PX = BX + BW + 40                             # HUD panel
PW = W - PX - 56

check_at = [(c["label"], c["at_ms"]) for c in trace["checks"]]


def frame_at(t):
    """Browser jpeg for wall-second t (t measured from the run start)."""
    key = min((ts for ts in times if ts - t0_wall >= t - 0.08), default=times[-1])
    return Image.open(d / "frames" / frames[key]).convert("RGB").resize((BW, BH), Image.LANCZOS)


def rounded(draw, box, r, fill, outline=None, width=1):
    draw.rounded_rectangle(box, r, fill=fill, outline=outline, width=width)


def check_mark(draw, x, y, done):
    r = 13
    if done:
        draw.ellipse([x, y, x + 2 * r, y + 2 * r], fill=GREEN)
        draw.line([x + 7, y + r + 1, x + 11, y + r + 6], fill=(10, 14, 10), width=3)
        draw.line([x + 11, y + r + 6, x + 19, y + r - 5], fill=(10, 14, 10), width=3)
    else:
        draw.ellipse([x, y, x + 2 * r, y + 2 * r], outline=DIM, width=2)


out = d / "render"
out.mkdir(exist_ok=True)
for n in range(N):
    t = n / FPS
    img = Image.new("RGB", (W, H), (11, 13, 16))
    dr = ImageDraw.Draw(img)

    # top band
    dr.text((60, 34), "jev-tern", font=f_brand, fill=WHITE)
    bw = dr.textlength("REAL WEB · 1× SPEED", font=f_badge)
    rounded(dr, [W - 60 - bw - 36, 34, W - 60, 84], 14, (24, 28, 34))
    dr.text((W - 60 - bw - 18, 44), "REAL WEB · 1× SPEED", font=f_badge, fill=GREY)
    head = f"Zürich → London. In {trace['elapsed_s']:.1f} seconds."
    dr.text((60, 62), head, font=f_head, fill=WHITE)
    dr.text((62, 154 - 12), "One sentence in · one judged step at a time", font=f_sub, fill=GREY)

    # browser window
    rounded(dr, [BX - 10, BY - 10, BX + BW + 10, BY + BH + 10], 18, (18, 21, 26), (38, 44, 52), 2)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        dr.ellipse([BX + 8 + i * 26, BY + 6, BX + 24 + i * 26, BY + 22], fill=c)
    img.paste(frame_at(t), (BX, BY))

    # HUD panel
    rounded(dr, [PX, BY, PX + PW, BY + BH], 18, (17, 20, 25), (34, 40, 48), 2)
    y = BY + 34

    dr.text((PX + 36, y), "LIVE RUN", font=f_label, fill=DIM)
    y += 30
    done = t >= trace["runEndOffset"] / 1000
    clock = f"{trace['elapsed_s']:.1f} s" if done else f"{t:.1f} s"
    dr.text((PX + 30, y), clock, font=f_clock, fill=GREEN if done else WHITE)
    y += 140
    dr.text((PX + 36, y), "SECONDS ELAPSED", font=f_label, fill=DIM)
    y += 70

    for label, at_ms in check_at:
        tick = bool(at_ms and t * 1000 >= at_ms)
        check_mark(dr, PX + 36, y, tick)
        dr.text((PX + 36 + 42, y + 1), label, font=f_item, fill=WHITE if tick else GREY)
        y += 58

    y += 26
    rounded(dr, [PX + 24, y, PX + PW - 24, y + 108], 14, (21, 25, 31))
    dr.text((PX + 44, y + 16), f"{trace['actions']} actions executed", font=f_stat, fill=WHITE)
    med = trace["median_decide_ms"]
    dr.text((PX + 44, y + 62), f"{med} ms median decision", font=f_statlab, fill=GREY)
    y += 132
    if done:
        rounded(dr, [PX + 24, y, PX + PW - 24, y + 108], 14, (16, 32, 24), (34, 84, 52), 2)
        dr.text((PX + 44, y + 14), "Verified after the run", font=f_statlab, fill=GREEN)
        dr.text((PX + 44, y + 46), "route · date · one-way · results", font=f_item, fill=WHITE)

    # bottom band
    prog = min(n / (N - 1), 1)
    rounded(dr, [60, H - 58, W - 60, H - 40], 9, (24, 28, 34))
    if prog > 0:
        rounded(dr, [60, H - 58, 60 + max(prog * (W - 120), 18), H - 40], 9, GREEN)
    dr.text((60, H - 32), "Operation + target by Jev · text by GLM-5.3-Flash · original timing, waits included",
            font=f_foot, fill=DIM)
    repo = "github.com/cyriusweng/jev-tern"
    dr.text((W - 60 - dr.textlength(repo, font=f_foot), H - 32), repo, font=f_foot, fill=GREY)

    img.save(out / f"frame-{n:05d}.jpg", quality=92)

print(N, "frames ->", out)
