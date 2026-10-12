import sqlite3
import requests
from bs4 import BeautifulSoup
import re

DB_FILE = "database.db"

# Ağrı'dan Ankara'ya kadar güzergahtaki iller
ALLOWED_CITIES = [
    "agri", "erzurum", "erzincan", "sivas", "kayseri", "yozgat", 
    "kirikkale", "ankara", "kars", "igdir", "mus", "van", "malatya", 
    "elazig", "tokat", "amasya", "corum", "kirsehir", "nevsehir"
]

# Arabam.com otomatik vites & max 1.2M TL kategori linkleri
TARGET_URLS = {
    "Renault Clio": "https://www.arabam.com/ikinci-el/otomobil/renault-clio?gear=2&price_max=1200000",
    "Hyundai Bayon": "https://www.arabam.com/ikinci-el/otomobil/hyundai-bayon?gear=2&price_max=1200000",
    "Hyundai i20": "https://www.arabam.com/ikinci-el/otomobil/hyundai-i20?gear=2&price_max=1200000",
    "Kia Stonic": "https://www.arabam.com/ikinci-el/otomobil/kia-stonic?gear=2&price_max=1200000",
    "Fiat Egea": "https://www.arabam.com/ikinci-el/otomobil/fiat-egea?gear=2&price_max=1200000",
    "Fiat Egea Cross": "https://www.arabam.com/ikinci-el/otomobil/fiat-egea-cross?gear=2&price_max=1200000"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9"
}

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("DROP TABLE IF EXISTS listings")
        conn.execute("""
            CREATE TABLE listings (
                id TEXT PRIMARY KEY,
                model_category TEXT,
                title TEXT,
                price TEXT,
                location TEXT,
                image_url TEXT,
                gear_type TEXT,
                url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

def scrape_category(model_name, url):
    print(f"--> [{model_name}] çekiliyor...")
    results = []
    try:
        res = requests.get(url, headers=HEADERS, timeout=20)
        if res.status_code != 200:
            print(f"Hata kodu: {res.status_code}")
            return results

        soup = BeautifulSoup(res.text, "html.parser")
        rows = soup.select("tr.listing-list-item")
        print(f"Bulunan satır ({model_name}): {len(rows)}")

        for row in rows:
            link_tag = row.select_one("td.horizontal-half-paddings a")
            if not link_tag:
                continue

            href = link_tag.get("href", "")
            title = link_tag.get("title", "").strip()
            item_id = row.get("id") or href

            # Gerçek Araç Fotoğrafı
            img_tag = row.select_one("img")
            img_url = ""
            if img_tag:
                img_url = img_tag.get("src") or img_tag.get("data-src") or ""
                # Küçük önizleme yerine kaliteli boyuta çevir
                img_url = img_url.replace("120x90", "580x435")

            # Fiyat
            price_tag = row.select_one("td.listing-price")
            price = price_tag.get_text(strip=True) if price_tag else "Fiyat Belirtilmemiş"

            # Konum
            loc_tag = row.select_one("td.listing-location-city")
            location = loc_tag.get_text(strip=True) if loc_tag else "Türkiye"

            # Şehir Kontrolü (Ağrı - Ankara hattı)
            loc_lower = location.lower()
            if not any(city in loc_lower for city in ALLOWED_CITIES):
                continue

            results.append((
                str(item_id),
                model_name,
                title,
                price,
                location,
                img_url,
                "Otomatik",
                f"https://www.arabam.com{href}" if not href.startswith("http") else href
            ))
    except Exception as e:
        print(f"Hata ({model_name}): {e}")

    return results

def run():
    init_db()
    all_data = []
    for model, url in TARGET_URLS.items():
        items = scrape_category(model, url)
        all_data.extend(items)

    with sqlite3.connect(DB_FILE) as conn:
        if all_data:
            conn.executemany("""
                INSERT OR REPLACE INTO listings (id, model_category, title, price, location, image_url, gear_type, url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, all_data)
            print(f"Bitti! Gerçek fotoğraflı {len(all_data)} adet canlı ilan kaydedildi.")
        else:
            print("İlan bulunamadı.")

if __name__ == "__main__":
    run()
