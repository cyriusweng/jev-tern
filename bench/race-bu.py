# One recorded browser-use run, for the race demo video.
# The recorder attaches over CDP and screencasts whatever page the agent opens,
# saving JPEG frames with unix timestamps to race-right/manifest.txt.
# Usage: bench/.venv/bin/python bench/race-bu.py
import asyncio, base64, glob, json, os, subprocess, time
from pathlib import Path

OUT = Path(__file__).parent.parent / "race-right"
FRAMES = OUT / "frames"
FRAMES.mkdir(parents=True, exist_ok=True)

TASK = ("Search Wikipedia for the Rosetta Stone, open the article, "
        "and jump to the \"Rediscovery\" section.")

def zai_key():
    env = os.environ.get("BU_KEY")
    if env:
        return env
    omp = os.environ.get("OMP_BIN", "omp")
    return subprocess.run([omp, "token", "zai"], capture_output=True, text=True).stdout.strip()


def find_chromium():
    env = os.environ.get("BU_BROWSER_PATH")
    if env:
        return env
    for pat in ["~/Library/Caches/ms-playwright/chromium-*/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
                "~/.cache/ms-playwright/chromium-*/chrome-linux/chrome"]:
        hits = sorted(glob.glob(os.path.expanduser(pat)))
        if hits:
            return hits[-1]
    return None


async def record_agent_pages(pw, t0):
    """Screencast every page the agent opens, until stop_event set, with acks."""
    conn = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
    manifest = open(FRAMES / "manifest.txt", "w")
    sessions = {}

    async def attach(context):
        for page in context.pages:
            if page in sessions:
                continue
            try:
                s = await context.new_cdp_session(page)
            except Exception:
                continue
            sessions[page] = s

            def on_frame(ev, s=s):
                ts = time.time()
                name = f"f{len(sessions):02d}_{int((ts - t0) * 1000):07d}.jpg"
                (FRAMES / name).write_bytes(base64.b64decode(ev["data"]))
                manifest.write(f"{ts:.3f} {name}\n")
                manifest.flush()
                asyncio.ensure_future(s.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]}))

            s.on("Page.screencastFrame", on_frame)
            await s.send("Page.startScreencast",
                         {"format": "jpeg", "quality": 92, "maxWidth": 1200, "maxHeight": 1000})

    for ctx in conn.contexts:
        await attach(ctx)

    async def watch():
        while True:
            for ctx in conn.contexts:
                await attach(ctx)
            await asyncio.sleep(0.5)

    watcher = asyncio.create_task(watch())
    return conn, manifest, watcher


async def main():
    from browser_use import Agent
    from browser_use.browser.profile import BrowserProfile
    from browser_use.browser.session import BrowserSession
    from browser_use.llm import ChatOpenAI
    from playwright.async_api import async_playwright

    llm = ChatOpenAI(
        base_url=os.environ.get("BU_BASE_URL", "https://open.bigmodel.cn/api/coding/paas/v4"),
        model=os.environ.get("BU_MODEL", "glm-5.3"),
        api_key=zai_key(),
        temperature=0,
    )
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, executable_path=find_chromium(),
                                           args=["--remote-debugging-port=9333"])
        t0 = time.time()
        conn, manifest, watcher = await record_agent_pages(pw, t0)
        session = BrowserSession(
            cdp_url="http://127.0.0.1:9333",
            browser_profile=BrowserProfile(viewport={"width": 600, "height": 500},
                                           device_scale_factor=2),
        )
        agent = Agent(task=TASK, llm=llm, browser_session=session,
                      max_steps=25, use_vision=False)
        hist = await agent.run()
        wall = round(time.time() - t0, 1)
        urls = [str(e.state.url or "") for e in hist.history if e.state]
        titles = [str(e.state.title or "") for e in hist.history if e.state]
        final = hist.final_result() or ""
        ok = any("Rosetta_Stone" in u for u in urls) and "discovery" in (final + " ".join(titles)).lower()
        await asyncio.sleep(1.0)
        watcher.cancel()
        manifest.close()
        await session.stop()
        await conn.close()
        await browser.close()
        print(json.dumps({"wall_s": wall, "success": ok, "final": final[:80]}))


asyncio.run(main())
