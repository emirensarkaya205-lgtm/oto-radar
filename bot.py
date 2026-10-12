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

    # ScraperAPI'nin Cloudflare ve bot duvarını aşan tarayıcı modu
    params = {
        'api_key': API_KEY,
        'url': target_url,
        'render': 'true',
        'country_code': 'tr'
    }

    try:
        response = requests.get('https://api.scraperapi.com/', params=params, timeout=120)
        print(f"[{model_name}] Yanıt Kodu: {response.status_code}")

        if response.status_code == 200:
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
        print("HATA: SCRAPER_API_KEY eksik!")
        return

    all_items = []
    for model_name, url in TARGET_URLS.items():
        items = scrape_category(model_name, url)
        all_items.extend(items)

    with sqlite3.connect(DB_FILE) as conn:
        if all_items:
            conn.executemany("""
                INSERT INTO listings (id, model_category, title, price, location, url)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    price = excluded.price,
                    location = excluded.location
            """, all_items)
            print(f"Başarılı! Toplam {len(all_items)} ilan kaydedildi.")
        else:
            print("Canlı ilan çekilemedi, test verisi hazırlanıyor...")
            # Sahibinden koruması sürerken sitenin boş kalmaması için ilk test verileri
            demo_items = [
                ("101", "Renault Clio", "2023 Renault Clio 1.0 TCe Touch Otomatik", "920.000 TL", "İstanbul / Kadıköy", "https://www.sahibinden.com/renault-clio"),
                ("102", "Hyundai i20", "2022 Hyundai i20 1.4 MPI Style Otomatik", "880.000 TL", "Ankara / Çankaya", "https://www.sahibinden.com/hyundai-i20"),
                ("103", "Hyundai Bayon", "2023 Hyundai Bayon 1.4 MPI Elite", "1.050.000 TL", "İzmir / Bornova", "https://www.sahibinden.com/hyundai-bayon"),
                ("104", "Kia Stonic", "2022 Kia Stonic 1.4 Cool Otomatik", "965.000 TL", "Bursa / Nilüfer", "https://www.sahibinden.com/kia-stonic"),
                ("105", "Fiat Egea", "2023 Fiat Egea Sedan 1.4 Fire Urban", "795.000 TL", "Antalya / Muratpaşa", "https://www.sahibinden.com/fiat-egea"),
                ("106", "Fiat Egea Cross", "2023 Fiat Egea Cross 1.5 T4 Hibrit Lounge", "1.180.000 TL", "Kocaeli / İzmit", "https://www.sahibinden.com/fiat-egea-cross"),
            ]
            conn.executemany("""
                INSERT OR IGNORE INTO listings (id, model_category, title, price, location, url)
                VALUES (?, ?, ?, ?, ?, ?)
            """, demo_items)
            print("Örnek araç kartları başarıyla yüklendi!")

if __name__ == "__main__":
    run()
