import os
import sqlite3
import requests
from bs4 import BeautifulSoup

DB_FILE = "database.db"
API_KEY = os.getenv("SCRAPER_API_KEY")

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

def scrape_category(model_name, target_url):
    print(f"--> [{model_name}] taranıyor...")
    results = []
    
    # ScraperAPI üzerinden Cloudflare korumasını aşarak HTML alma
    proxy_url = f"http://api.scraperapi.com?api_key={API_KEY}&url={target_url}&country_code=tr"
    
    try:
        response = requests.get(proxy_url, timeout=60)
        if response.status_code != 200:
            print(f"Hata kodu ({model_name}): {response.status_code}")
            return results

        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.select("tr.searchResultsItem:not(.nativeAd)")
        print(f"Bulunan satır sayısı ({model_name}): {len(rows)}")

        for row in rows:
            row_id = row.get("data-id")
            if not row_id:
                continue

            title_el = row.select_one("td.searchResultsTitleValue a")
            price_el = row.select_one("td.searchResultsPriceValue")
            loc_el = row.select_one("td.searchResultsLocationValue")

            if title_el and price_el:
                title_txt = title_el.get_text(strip=True)
                href = title_el.get("href", "")
                price_txt = price_el.get_text(strip=True).replace("\n", " ")
                loc_txt = loc_el.get_text(strip=True).replace("\n", " ") if loc_el else "Belirtilmemiş"

                results.append((
                    row_id,
                    model_name,
                    title_txt,
                    price_txt,
                    loc_txt,
                    f"https://www.sahibinden.com{href}"
                ))
    except Exception as e:
        print(f"Hata ({model_name}): {e}")
        
    return results

def run():
    init_db()
    if not API_KEY:
        print("HATA: SCRAPER_API_KEY tanımlanmamış!")
        return

    all_items = []
    for model_name, url in TARGET_URLS.items():
        items = scrape_category(model_name, url)
        all_items.extend(items)

    if all_items:
        with sqlite3.connect(DB_FILE) as conn:
            conn.executemany("""
                INSERT INTO listings (id, model_category, title, price, location, url)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    price = excluded.price,
                    location = excluded.location
            """, all_items)
        print(f"Başarılı! Toplam {len(all_items)} ilan kaydedildi.")
    else:
        print("Hiç ilan kaydedilemedi.")

if __name__ == "__main__":
    run()
