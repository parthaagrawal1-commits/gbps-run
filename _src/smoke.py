import asyncio, re, os
from playwright.async_api import async_playwright

BIG = b"x" * 2_000_000

async def main():
    errors = []
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        ctx = await b.new_context(viewport={"width": 430, "height": 932}, device_scale_factor=2)
        page = await ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)

        async def handler(route):
            url = route.request.url
            if "/__down" in url:
                m = re.search(r"bytes=(\d+)", url); n = int(m.group(1)) if m else 0
                body = b"" if n == 0 else BIG
                await route.fulfill(status=200, body=body, headers={"access-control-allow-origin": "*", "server-timing": "cfRequestDuration;dur=0.4", "access-control-expose-headers": "server-timing"})
            elif "/__up" in url:
                await route.fulfill(status=200, body="ok", headers={"access-control-allow-origin": "*"})
            elif "/meta" in url:
                await route.fulfill(status=200, body='{"clientIp":"203.0.113.9","asOrganization":"Example ISP","colo":"SLC","city":"Salt Lake City","httpProtocol":"HTTP/2"}', headers={"access-control-allow-origin": "*", "content-type": "application/json"})
            else:
                await route.fulfill(status=404, body="")
        await page.route("**/speed.cloudflare.com/**", handler)
        await page.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, body="", headers={"content-type": "text/css"}))

        await page.goto("file://" + os.path.abspath(os.environ.get("PAGE","site/index.html")))
        await page.screenshot(path="shot_idle.png")
        await page.click("#settingsBtn")
        await page.select_option("#durSel", "6")
        await page.click("#startBtn")
        await page.wait_for_function("document.getElementById('phase').textContent.startsWith('Done')", timeout=40000)
        await page.fill("#planIn", "1000")
        await page.wait_for_timeout(500)
        await page.screenshot(path="shot_done.png", full_page=True)
        res = await page.evaluate("""() => ({
            down: document.getElementById('tDown').textContent, up: document.getElementById('tUp').textContent,
            ping: document.getElementById('tPing').textContent, bloat: document.getElementById('tBloat').textContent,
            verdicts: document.querySelectorAll('#verdicts .verdict').length, plan: document.getElementById('planText').textContent,
            meta: document.getElementById('meta').textContent, hist: document.querySelectorAll('#histTable tbody tr').length,
            share: document.getElementById('shareText').textContent })""")
        print(res)
        await page.click("#copyBtn")
        await page.click("#themeBtn")
        await page.screenshot(path="shot_light.png")
        await b.close()
    print("ERRORS:", errors)

asyncio.run(main())
