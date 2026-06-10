import asyncio
import re

from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = await ctx.new_page()
        await page.goto(
            "https://www.shwapno.com/SearchResults.aspx?search=rice",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        await page.wait_for_timeout(10000)
        html = await page.content()
        for needle in ["searchTerm", "searchQuery", "SearchResults", "totalProducts", "productList"]:
            print(needle, html.count(needle))
        # slice between SearchResults and first unrelated section
        idx = html.find("Search result")
        print("Search result idx", idx)
        if idx < 0:
            idx = html.find("SearchResults")
        if idx >= 0:
            chunk = html[idx : idx + 200000]
            rice = re.findall(r'\\"name\\":\\"([^\\"]*[Rr]ice[^\\"]*)\\"', chunk)
            print("rice in chunk", len(rice), rice[:15])
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
