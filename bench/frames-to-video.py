# Convert screencast frames + manifest.txt into a CFR 25fps video whose timeline
# starts at the engine's runStart when timing.json exists (drops warm-up frames).
# Usage: bench/.venv/bin/python bench/frames-to-video.py race-left
import json, subprocess, sys
from pathlib import Path

d = Path(sys.argv[1])
rows = [ln.split() for ln in (d / "frames" / "manifest.txt").read_text().splitlines() if ln.strip()]

t0 = float(rows[0][0])
timing = d / "timing.json"
if timing.exists():
    tj = json.loads(timing.read_text())
    run_start = tj["runStart"] / 1000
    rows = [r for r in rows if float(r[0]) >= run_start]
    t0 = run_start

with (d / "list.txt").open("w") as f:
    for i, (ts, name) in enumerate(rows):
        dur = (float(rows[i + 1][0]) - float(ts)) if i + 1 < len(rows) else 2.5
        f.write(f"file 'frames/{name}'\nduration {max(dur, 0.001):.3f}\n")
    f.write(f"file 'frames/{rows[-1][1]}'\n")

out = d / "right.mp4"
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(d / "list.txt"),
                "-vf", "fps=25,scale=1200:1000,setsar=1", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-crf", "20", str(out)], check=True)
total = float(rows[-1][0]) - t0 + 2.5
print(json.dumps({"out": str(out), "wall_s": round(total, 1)}))
