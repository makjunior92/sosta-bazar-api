import re

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.scrapers.base import RawOffer, StoreAdapter
from app.services.unit_price import compute_unit_price, parse_price


class ChaldalAdapter(StoreAdapter):
    store_slug = "chaldal"
    store_name = "Chaldal"

    async def search(self, query: str, area: str | None = None) -> list[RawOffer]:
        url = f"https://chaldal.com/search/{query.replace(' ', '%20')}"
        offers: list[RawOffer] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle", timeout=60000)

            for _ in range(5):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(800)

            html = await page.content()
            await browser.close()

        soup = BeautifulSoup(html, "lxml")
        for item in soup.find_all("div", class_="product"):
            name_el = item.find("div", class_="name")
            price_el = item.find("div", class_="price")
            if not name_el or not price_el:
                continue
            title = re.sub(r"<.*?>", "", str(name_el)).strip()
            if not re.search(query, title, re.IGNORECASE):
                continue
            price = parse_price(re.sub(r"<.*?>", "", str(price_el)))
            if price is None:
                continue
            link_el = item.find("a", class_="btnShowDetails")
            img_el = item.find("img")
            href = link_el.get("href", "") if link_el else ""
            product_url = f"https://chaldal.com{href}" if href.startswith("/") else href
            image_url = img_el.get("src") if img_el else None
            offers.append(
                RawOffer(
                    title=title,
                    price_bdt=price,
                    product_url=product_url or url,
                    image_url=image_url,
                    unit_price_bdt=compute_unit_price(price, title),
                )
            )
        return offers

    async def health_check(self) -> bool:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                resp = await page.goto("https://chaldal.com", timeout=30000)
                await browser.close()
                return resp is not None and resp.ok
        except Exception:
            return False
