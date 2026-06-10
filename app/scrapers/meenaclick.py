import re

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.scrapers.base import RawOffer, StoreAdapter
from app.services.unit_price import compute_unit_price, parse_price


class MeenaClickAdapter(StoreAdapter):
    store_slug = "meenaclick"
    store_name = "MeenaClick"

    async def search(self, query: str, area: str | None = None) -> list[RawOffer]:
        url = f"https://www.meenaclick.com/search?q={query.replace(' ', '+')}"
        offers: list[RawOffer] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle", timeout=60000)
            html = await page.content()
            await browser.close()

        soup = BeautifulSoup(html, "lxml")
        for item in soup.select(".product-item, .product-card, [class*='product']"):
            title_el = item.select_one("h2, h3, h4, .product-name, .title, a[title]")
            price_el = item.select_one(".price, .product-price, [class*='price']")
            if not title_el:
                continue
            title = title_el.get("title") or title_el.get_text(strip=True)
            if len(title) < 3 or not re.search(query, title, re.IGNORECASE):
                continue
            price_text = price_el.get_text(strip=True) if price_el else ""
            price = parse_price(price_text)
            if price is None:
                continue
            link_el = item.find("a", href=True)
            href = link_el["href"] if link_el else url
            product_url = href if href.startswith("http") else f"https://www.meenaclick.com{href}"
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
                resp = await page.goto("https://www.meenaclick.com", timeout=30000)
                await browser.close()
                return resp is not None and resp.ok
        except Exception:
            return False
