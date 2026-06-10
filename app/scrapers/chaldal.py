import re
from decimal import Decimal

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.scrapers.base import RawOffer, StoreAdapter
from app.services.unit_price import compute_unit_price, parse_price

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class ChaldalAdapter(StoreAdapter):
    store_slug = "chaldal"
    store_name = "Chaldal"

    async def search(self, query: str, area: str | None = None) -> list[RawOffer]:
        url = f"https://chaldal.com/search/{query.replace(' ', '%20')}"
        offers: list[RawOffer] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=USER_AGENT)
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            try:
                await page.wait_for_selector(".productV2Catalog", timeout=30000)
            except Exception:
                await page.wait_for_timeout(5000)

            for _ in range(6):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(500)

            html = await page.content()
            await browser.close()

        soup = BeautifulSoup(html, "lxml")
        for card in soup.find_all("div", class_="productV2Catalog"):
            classes = card.get("class") or []
            if "outOfStock" in classes:
                continue

            name_el = card.select_one(".pvName, .nameTextWithEllipsis")
            if not name_el:
                continue
            title = name_el.get_text(strip=True)

            unit_text = ""
            sub = card.select_one(".subText")
            if sub:
                unit_span = sub.find("span")
                if unit_span:
                    unit_text = unit_span.get_text(strip=True)
            full_title = f"{title} {unit_text}".strip() if unit_text else title

            price = self._extract_price(card)
            if price is None:
                continue

            img = card.find("img")
            image_url = img.get("src") if img else None
            product_url = self._product_url_from_image(image_url) or url

            offers.append(
                RawOffer(
                    title=full_title,
                    price_bdt=price,
                    product_url=product_url,
                    image_url=image_url,
                    unit_price_bdt=compute_unit_price(price, full_title),
                )
            )
        return offers

    def _extract_price(self, card) -> Decimal | None:
        price_block = card.select_one(".productV2discountedPrice")
        if price_block:
            for span in price_block.find_all("span"):
                text = span.get_text(strip=True)
                if text.isdigit():
                    return Decimal(text)
            parsed = parse_price(price_block.get_text(" ", strip=True))
            if parsed is not None:
                return parsed

        legacy = card.select_one(".price span")
        if legacy:
            text = legacy.get_text(strip=True)
            if text.isdigit():
                return Decimal(text)
            return parse_price(legacy.get_text(strip=True))

        return parse_price(card.get_text(" ", strip=True))

    def _product_url_from_image(self, image_url: str | None) -> str | None:
        if not image_url:
            return None
        match = re.search(r"_mpimage/([^?]+)", image_url)
        if match:
            return f"https://chaldal.com/{match.group(1)}"
        return None

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
