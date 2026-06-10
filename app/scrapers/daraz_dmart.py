import re

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.scrapers.base import RawOffer, StoreAdapter
from app.services.unit_price import compute_unit_price, parse_price


class DarazDmartAdapter(StoreAdapter):
    store_slug = "daraz-dmart"
    store_name = "Daraz dMart"

    async def search(self, query: str, area: str | None = None) -> list[RawOffer]:
        url = f"https://www.daraz.com.bd/catalog/?q={query.replace(' ', '+')}&_keyori=ss&from=input&spm=a2a0e.searchlist.search.go"
        offers: list[RawOffer] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)
            html = await page.content()
            await browser.close()

        soup = BeautifulSoup(html, "lxml")
        for item in soup.select("[class*='GridItem'], .gridItem, div[data-qa-locator='product-item']"):
            title_el = item.select_one("[class*='title'], .title--wrap, a[title]")
            price_el = item.select_one("[class*='price'], .currency")
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
            product_url = href if href.startswith("http") else f"https://www.daraz.com.bd{href}"
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
                resp = await page.goto("https://www.daraz.com.bd/dmart/", timeout=30000)
                await browser.close()
                return resp is not None and resp.ok
        except Exception:
            return False
