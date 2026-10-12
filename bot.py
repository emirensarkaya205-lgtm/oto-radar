import asyncio
import sqlite3
import random
from playwright.async_api import async_playwright

DB_FILE = "database.db"

TARGET_URLS = {
    "Renault Clio": "https://www.sahibinden.com/renault-clio",
    "Hyundai Bayon": "https://www.sahibinden.com/hyundai-bayon",
    "Hyundai i20": "https://www.sahibinden.com/hyundai-i20",
    "Kia Stonic": "https://www.sahibinden.com/kia-stonic",
    "Fiat Egea": "https://www.sahibinden.com/fiat-egea",
    "Fiat Egea Cross": "https://www.sahibinden.com/fiat-egea-cross"
}

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                id TEXT PRIMARY KEY,
                model_category TEXT,
                title TEXT,
                price TEXT,
                location TEXT,
                url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

async def scrape_category(page, model_name, url):
    print(f"--> {model_name} taranıyor...")
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(random.uniform(2, 4))

        rows = await page.query_selector_all("tr.searchResultsItem:not(.nativeAd)")
        results = []

        for row in rows:
            row_id = await row.get_attribute("data-id")
            if not row_id:
                continue

            title_el = await row.query_selector("td.searchResultsTitleValue a")
            price_el = await row.query_selector("td.searchResultsPriceValue")
            loc_el = await row.query_selector("td.searchResultsLocationValue")

            if title_el and price_el:
                title = (await title_el.inner_text()).strip()
                href = await title_el.get_attribute("href")
                price = (await price_el.inner_text()).strip().replace("\n", " ")
                location = (await loc_el.inner_text()).strip().replace("\n", " ") if loc_el else "Belirtilmemiş"

                results.append((
                    row_id,
                    model_name,
                    title,
                    price,
                    location,
                    f"https://www.sahibinden.com{href}"
                ))
        return results
    except Exception as e:
        print(f"Hata ({model_name}): {e}")
        return []

async def run_scraper():
    init_db()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        all_items = []
        for model_name, url in TARGET_URLS.items():
            items = await scrape_category(page, model_name, url)
            all_items.extend(items)
            await asyncio.sleep(random.uniform(3, 5))

        await browser.close()

        with sqlite3.connect(DB_FILE) as conn:
            conn.executemany("""
                INSERT INTO listings (id, model_category, title, price, location, url)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    price = excluded.price,
                    location = excluded.location
            """, all_items)
        print(f"Bitti! Toplam {len(all_items)} ilan kaydedildi.")

if __name__ == "__main__":
    asyncio.run(run_scraper())
