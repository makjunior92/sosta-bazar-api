import re

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.scrapers.base import RawOffer, StoreAdapter
from app.services.unit_price import compute_unit_price, parse_price


class ShwapnoAdapter(StoreAdapter):
    store_slug = "shwapno"
    store_name = "Shwapno"

    async def search(self, query: str, area: str | None = None) -> list[RawOffer]:
        url = f"https://www.shwapno.com/SearchResults.aspx?search={query.replace(' ', '+')}"
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
        for item in soup.find_all("div", class_="bucket"):
            title_el = item.find("h4", class_="mtb-title")
            price_el = item.find("span", class_="sp_amt")
            if not title_el or not price_el:
                continue
            title = title_el.get_text(strip=True)
            if not re.search(query, title, re.IGNORECASE):
                continue
            price = parse_price(price_el.get_text(strip=True))
            if price is None:
                continue
            left = item.find("div", class_="bucket_left")
            link = left.find("a")["href"] if left and left.find("a") else url
            img_el = left.find("img", attrs={"original": True}) if left else None
            image_url = img_el.get("original") if img_el else None
            offers.append(
                RawOffer(
                    title=title,
                    price_bdt=price,
                    product_url=link,
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
                resp = await page.goto("https://www.shwapno.com", timeout=30000)
                await browser.close()
                return resp is not None and resp.ok
        except Exception:
            return False
