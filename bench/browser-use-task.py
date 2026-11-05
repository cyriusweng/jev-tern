# browser-use on the same three benchmark tasks, same success criteria.
# The bigmodel coding endpoint serves text-only messages, so the agent runs with
# use_vision=False over a locally launched CDP Chromium (one browser, nine runs).
# Setup:  cd bench && uv venv && uv pip install "browser-use==0.11.13" "playwright==1.64.*"
# Usage:  bench/.venv/bin/python bench/browser-use-task.py   (appends to bench/RESULTS.json)
# Env:    BU_MODEL (default glm-5.3), BU_BASE_URL, BU_BROWSER_PATH, OMP_BIN
import asyncio, glob, json, os, subprocess, time
from pathlib import Path

RESULTS = Path(__file__).parent / "RESULTS.json"
CDP_PORT = 9333

def zai_key():
    omp = os.environ.get("OMP_BIN", "omp")
    return subprocess.run([omp, "token", "zai"], capture_output=True, text=True).stdout.strip()

def find_chromium():
    """BU_BROWSER_PATH wins; else the newest Playwright-cached Chromium on any OS."""
    env = os.environ.get("BU_BROWSER_PATH")
    if env:
        return env
    patterns = [
        "~/Library/Caches/ms-playwright/chromium-*/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
        "~/Library/Caches/ms-playwright/chromium-*/chrome-mac/Chromium.app/Contents/MacOS/Chromium",
        "~/.cache/ms-playwright/chromium-*/chrome-linux/chrome",
        "~/AppData/Local/ms-playwright/chromium-*/chrome-win/chrome.exe",
    ]
    for pat in patterns:
        hits = sorted(glob.glob(os.path.expanduser(pat)))
        if hits:
            return hits[-1]
    return None

async def main():
    from browser_use import Agent
    from browser_use.browser.profile import BrowserProfile
    from browser_use.llm import ChatOpenAI
    from playwright.async_api import async_playwright

    llm = ChatOpenAI(
        base_url=os.environ.get("BU_BASE_URL", "https://open.bigmodel.cn/api/coding/paas/v4"),
        model=os.environ.get("BU_MODEL", "glm-5.3"),
        api_key=zai_key(),
        temperature=0,
    )

    TASKS = {
        "t1-fetch": ("Open https://en.wikipedia.org/wiki/Mona_Lisa and report who painted it.",
                     lambda urls, titles, r: "leonardo" in (r or "").lower()),
        "t2-portal": ("Open https://en.wikipedia.org/wiki/Main_Page and open today's featured article.",
                      lambda urls, titles, r: any("/wiki/" in u and ":" not in u.split("/wiki/")[-1]
                                                  and "Today" not in u and "Main_Page" not in u
                                                  for u in urls)),
        "t3-section": ("Open https://en.wikipedia.org/wiki/G%C3%B6del%27s_incompleteness_theorems and bring the References section heading into view.",
                       lambda urls, titles, r: "reference" in (r or "").lower()
                       or any("reference" in (t or "").lower() for t in titles)),
    }

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            executable_path=find_chromium(),
            args=[f"--remote-debugging-port={CDP_PORT}"],
        )
        profile = BrowserProfile(cdp_url=f"http://127.0.0.1:{CDP_PORT}")

        rows = json.loads(RESULTS.read_text()) if RESULTS.exists() else []
        rows = [r for r in rows if r.get("contender") != "browser-use"]
        for tid, (prompt, ok_fn) in TASKS.items():
            for run in range(1, 4):
                t0 = time.time()
                try:
                    agent = Agent(task=prompt, llm=llm, browser_profile=profile,
                                  max_steps=15, use_vision=False)
                    hist = await agent.run()
                    final = hist.final_result() or ""
                    titles = [str(e.state.title or "") for e in hist.history if e.state]
                    urls = [str(e.state.url or "") for e in hist.history if e.state]
                    steps = len([e for e in hist.history if e.model_output and e.model_output.action])
                    ok = ok_fn(urls, titles, final)
                    note = f"final={final[:60]!r}"
                except Exception as e:
                    steps, ok, note = 0, False, f"error={type(e).__name__}: {e}"[:120]
                wall = round(time.time() - t0, 1)
                rows.append(dict(task=tid, contender="browser-use", run=run,
                                 wall_s=wall, steps=steps, success=bool(ok), note=note))
                RESULTS.write_text(json.dumps(rows, indent=1))
                print(tid, "run", run, wall, "s", "OK" if ok else "FAIL", note, flush=True)
        await browser.close()

asyncio.run(main())
