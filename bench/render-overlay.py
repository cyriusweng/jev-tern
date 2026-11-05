# Render the transparent 25fps text layer for the race video: labels, ticking
# timers, DONE stamps, banner. Output: overlay-%05d.png in race-overlay/.
# Usage: bench/.venv/bin/python bench/render-overlay.py TJ TB TOT
import math, sys
from PIL import Image, ImageDraw, ImageFont

TJ, TB, TOT = float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3])
FPS = 25
N = math.ceil(TOT * FPS)
MENLO = "/System/Library/Fonts/Menlo.ttc"

f_big = ImageFont.truetype(MENLO, 64)
f_timer = ImageFont.truetype(MENLO, 72)
f_stamp = ImageFont.truetype(MENLO, 72)
f_note = ImageFont.truetype(MENLO, 44)
f_banner = ImageFont.truetype(MENLO, 54)


def text_box(draw, xy, text, font, fill, pad=18):
    x, y = xy
    w = draw.textlength(text, font=font)
    asc, desc = font.getmetrics()
    h = asc + desc
    draw.rounded_rectangle([x - pad, y - pad, x + w + pad, y + h + pad], 12, fill=(10, 10, 10, 216))
    draw.text((x, y), text, font=font, fill=fill)
    return w + 2 * pad, h + 2 * pad


def timer_text(n):
    return f"{n // FPS}.{(n * 10 // FPS) % 10} s"


FJ = round(TJ * FPS)
FB = round(TB * FPS)
CAPF = 180 * FPS
mins, secs = int(TB // 60), TB % 60

for n in range(N):
    img = Image.new("RGBA", (2400, 1000), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # left panel: jev-tern
    text_box(d, (40, 40), "jev-tern", f_big, (255, 255, 255, 255))
    t = f"DONE {TJ} s" if n >= FJ else timer_text(n)
    w = d.textlength(t, font=f_stamp)
    text_box(d, (1200 - 40 - w, 40), t, f_timer,
             (57, 255, 20, 255) if n >= FJ else (255, 255, 255, 255))

    # right panel: browser-use
    text_box(d, (1240, 40), "browser-use", f_big, (255, 255, 255, 255))
    if n < min(FB, CAPF):
        t = timer_text(n)
        w = d.textlength(t, font=f_timer)
        text_box(d, (2400 - 40 - w, 40), t, f_timer, (255, 255, 255, 255))
    elif n >= FB:
        t = f"DONE {TB} s"
        w = d.textlength(t, font=f_stamp)
        text_box(d, (2400 - 40 - w, 40), t, f_stamp, (255, 209, 102, 255))
    else:
        t = timer_text(n)
        w = d.textlength(t, font=f_timer)
        text_box(d, (2400 - 40 - w, 40), t, f_timer, (255, 255, 255, 255))
        t2 = f"still running, finished at {mins} min {secs:.1f} s"
        w2 = d.textlength(t2, font=f_note)
        text_box(d, (2400 - 40 - w2, 150), t2, f_note, (156, 163, 175, 255), pad=14)

    # banner
    t = "Search Wikipedia for the Rosetta Stone, open the article, jump to the Rediscovery section"
    w = d.textlength(t, font=f_note)
    text_box(d, ((2400 - w) / 2, 815), t, f_note, (156, 163, 175, 255), pad=14)
    t = "Same task · same machine · same API keys · real time"
    w = d.textlength(t, font=f_banner)
    asc, desc = f_banner.getmetrics()
    text_box(d, ((2400 - w) / 2, 1000 - (asc + desc) - 40), t, f_banner, (255, 255, 255, 255), pad=16)

    img.save(f"race-overlay/overlay-{n:05d}.png", compress_level=6)

print(N, "frames")
