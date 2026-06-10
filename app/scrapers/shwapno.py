import re
from decimal import Decimal

from playwright.async_api import async_playwright

from app.scrapers.base import RawOffer, StoreAdapter
from app.services.unit_price import compute_unit_price

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

PRODUCT_PATTERN = re.compile(
    r'\\"name\\":\\"([^\\"]+)\\".*?\\"seName\\":\\"([^\\"]+)\\".*?\\"priceValue\\":(\d+(?:\.\d+)?)',
    re.DOTALL,
)

IMAGE_PATTERN = re.compile(r'\\"seName\\":\\"' + r'([^\\"]+)' + r'\\".*?\\"imageUrl\\":\\"([^\\"]+)\\"', re.DOTALL)


class ShwapnoAdapter(StoreAdapter):
    store_slug = "shwapno"
    store_name = "Shwapno"

    async def search(self, query: str, area: str | None = None) -> list[RawOffer]:
        url = f"https://www.shwapno.com/SearchResults.aspx?search={query.replace(' ', '+')}"
        offers: list[RawOffer] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=USER_AGENT)
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(8000)

            for _ in range(6):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(500)

            html = await page.content()
            await browser.close()

        images = {slug: img for slug, img in IMAGE_PATTERN.findall(html)}

        seen: set[str] = set()
        query_lower = query.lower()
        for name, slug, price_str in PRODUCT_PATTERN.findall(html):
            if slug in seen:
                continue
            if query_lower not in name.lower() and query_lower not in slug.lower():
                continue
            seen.add(slug)
            price = Decimal(price_str)
            image_url = images.get(slug)
            if image_url and image_url.startswith("/"):
                image_url = f"https://www.shwapno.com{image_url}"
            offers.append(
                RawOffer(
                    title=name,
                    price_bdt=price,
                    product_url=f"https://www.shwapno.com/{slug}",
                    image_url=image_url,
                    external_id=slug,
                    unit_price_bdt=compute_unit_price(price, name),
                )
            )
        return offers

    async def health_check(self) -> bool:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(user_agent=USER_AGENT)
                page = await context.new_page()
                resp = await page.goto("https://www.shwapno.com", timeout=30000)
                await browser.close()
                return resp is not None and resp.ok
        except Exception:
            return False
