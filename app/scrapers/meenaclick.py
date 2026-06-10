import re

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.scrapers.base import RawOffer, StoreAdapter
from app.services.unit_price import compute_unit_price, parse_price

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class MeenaClickAdapter(StoreAdapter):
    store_slug = "meenaclick"
    store_name = "MeenaClick"

    async def search(self, query: str, area: str | None = None) -> list[RawOffer]:
        url = f"https://meenabazaronline.com/search?q={query.replace(' ', '+')}"
        offers: list[RawOffer] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=USER_AGENT)
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(5000)

            for _ in range(5):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(500)

            html = await page.content()
            await browser.close()

        soup = BeautifulSoup(html, "lxml")
        for item in soup.select(
            ".product-card, .product-item, [class*='product-card'], [class*='ProductCard'], .card"
        ):
            title_el = item.select_one("h2, h3, h4, h5, .product-name, .title, a")
            price_el = item.select_one(".price, [class*='price'], .amount")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if len(title) < 3:
                continue
            price = parse_price(price_el.get_text(strip=True) if price_el else "")
            if price is None:
                continue
            link_el = item.find("a", href=True)
            href = link_el["href"] if link_el else url
            product_url = href if href.startswith("http") else f"https://meenabazaronline.com{href}"
            img_el = item.find("img")
            offers.append(
                RawOffer(
                    title=title,
                    price_bdt=price,
                    product_url=product_url,
                    image_url=img_el.get("src") if img_el else None,
                    unit_price_bdt=compute_unit_price(price, title),
                )
            )
        return offers[:30]

    async def health_check(self) -> bool:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                resp = await page.goto("https://meenabazaronline.com", timeout=30000)
                await browser.close()
                return resp is not None and resp.ok
        except Exception:
            return False
