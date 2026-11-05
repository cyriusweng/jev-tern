import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));

async function loadPlaywright() {
  try {
    return await import("playwright");
  } catch {}
  try {
    return await import(join(__dirname, "bench/node_modules/playwright/index.mjs"));
  } catch {}
  throw new Error(
    "playwright not found. Install it with: npm install playwright && npx playwright install chromium"
  );
}

export async function createCdpBrowser(options = {}) {
  const pw = options.playwright || (await loadPlaywright());
  const cdpUrl = options.cdpUrl || process.env.CDP_URL;
  const headless =
    options.headless ??
    (process.env.HEADLESS === "1" || process.env.HEADLESS === "true");
  // Snapshot size scales with the viewport; 600x500 matches the engine's tuned budget.
  const viewport = options.viewport || { width: 600, height: 500 };
  const recordVideo = options.recordVideo || null;
  const deviceScaleFactor = options.deviceScaleFactor || 1;
  const launchArgs = options.launchArgs || [];
  let pwBrowser = options.browser || null;
  let ownsBrowser = false;

  if (!pwBrowser) {
    if (cdpUrl) {
      pwBrowser = await pw.chromium.connectOverCDP(cdpUrl);
    } else {
      pwBrowser = await pw.chromium.launch({
        headless,
        args: [
          "--no-default-browser-check",
          "--no-first-run",
          "--disable-blink-features=AutomationControlled",
          ...launchArgs,
        ],
      });
      ownsBrowser = true;
    }
  }

  const contexts = new Map();
  const tabs = new Map();

  async function getOrCreateTab(name, url, waitUntil = "domcontentloaded") {
    let tab = tabs.get(name);
    if (tab && !tab.page.isClosed()) {
      if (url && url !== "about:blank") {
        await tab.page.goto(url, { waitUntil, timeout: 30000 });
      }
      return tab;
    }

    let context = contexts.get(name);
    if (!context) {
      context = await pwBrowser.newContext({ viewport, deviceScaleFactor, ...(recordVideo ? { recordVideo } : {}) });
    }

    const page = await context.newPage();
    let allowedList = null;

    page.on("framenavigated", async (frame) => {
      if (frame === page.mainFrame() && allowedList && allowedList.length > 0) {
        try {
          const u = new URL(frame.url());
          if (u.protocol.startsWith("http")) {
            const host = u.hostname.toLowerCase();
            const allowed = allowedList.some(
              (d) => host === d || host.endsWith("." + d)
            );
            if (!allowed) {
              console.warn(
                `[cdp-bridge] Blocked navigation out of allowed domains: ${host}`
              );
              await page.goBack().catch(() => {});
            }
          }
        } catch {}
      }
    });

    if (url && url !== "about:blank") {
      await page.goto(url, { waitUntil, timeout: 30000 });
    }

    tab = {
      name,
      page,
      evaluate: async (script) => {
        return await page.evaluate(script);
      },
      clickAt: async (x, y) => {
        await page.mouse.click(x, y);
      },
      title: async () => {
        return await page.title();
      },
      allowedDomains: async (list) => {
        allowedList = Array.isArray(list)
          ? list.map((d) => d.toLowerCase())
          : null;
      },
      run: async (fn) => {
        return await fn({ page });
      },
      close: async () => {
        tabs.delete(name);
        await page.close().catch(() => {});
      },
    };

    tabs.set(name, tab);
    return tab;
  }

  const browser = {
    open: async (opts) => {
      const { name = "jev-tern", url = "about:blank", wait_until = "domcontentloaded" } = opts;
      return await getOrCreateTab(name, url, wait_until);
    },
    getTab: (name) => tabs.get(name),
    close: async () => {
      for (const tab of tabs.values()) {
        await tab.page.close().catch(() => {});
      }
      tabs.clear();
      for (const ctx of contexts.values()) {
        await ctx.close().catch(() => {});
      }
      contexts.clear();
      if (ownsBrowser && pwBrowser) {
        await pwBrowser.close().catch(() => {});
      }
    },
  };

  return browser;
}

export async function attachCdpBridge(options = {}) {
  const browser = await createCdpBrowser(options);
  globalThis.browser = browser;
  return browser;
}
