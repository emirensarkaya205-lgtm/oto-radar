import sqlite3
import requests
from bs4 import BeautifulSoup
import urllib.parse

DB_FILE = "database.db"

# Ağrı'dan Ankara'ya kadar uzanan güzergah şehirleri (plaka kodları veya isim eşleşmeleri)
CITIES = [
    "Ağrı", "Erzurum", "Erzincan", "Sivas", "Kayseri", "Yozgat", 
    "Kırıkkale", "Ankara", "Kars", "Iğdır", "Muş", "Van", "Malatya", 
    "Elazığ", "Tokat", "Amasya", "Çorum", "Kırşehir", "Nevşehir"
]

TARGETS = [
    {"name": "Renault Clio", "url": "https://www.arabam.com/ikinci-el/otomobil/renault-clio?gear=2&price_max=1200000&take=50"},
    {"name": "Hyundai Bayon", "url": "https://www.arabam.com/ikinci-el/otomobil/hyundai-bayon?gear=2&price_max=1200000&take=50"},
    {"name": "Hyundai i20", "url": "https://www.arabam.com/ikinci-el/otomobil/hyundai-i20?gear=2&price_max=1200000&take=50"},
    {"name": "Kia Stonic", "url": "https://www.arabam.com/ikinci-el/otomobil/kia-stonic?gear=2&price_max=1200000&take=50"},
    {"name": "Fiat Egea", "url": "https://www.arabam.com/ikinci-el/otomobil/fiat-egea?gear=2&price_max=1200000&take=50"},
    {"name": "Fiat Egea Cross", "url": "https://www.arabam.com/ikinci-el/otomobil/fiat-egea-cross?gear=2&price_max=1200000&take=50"}
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
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

def clean_text(text):
    return " ".join(text.split()) if text else ""

def scrape():
    init_db()
    all_rows = []

    for target in TARGETS:
        model = target["name"]
        url = target["url"]
        print(f"--> [{model}] taranıyor...")

        try:
            res = requests.get(url, headers=HEADERS, timeout=25)
            if res.status_code != 200:
                print(f"Hata: {res.status_code}")
                continue

            soup = BeautifulSoup(res.text, "html.parser")
            rows = soup.select("tr.listing-list-item")
            print(f"Bulunan ilan ({model}): {len(rows)}")

            for row in rows:
                link_el = row.select_one("td.horizontal-half-paddings
