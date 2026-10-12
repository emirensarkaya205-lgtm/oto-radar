import sqlite3
from curl_cffi import requests
from bs4 import BeautifulSoup

DB_FILE = "database.db"

# Doğu Anadolu, Güneydoğu Anadolu, Kuzeydoğu ve Ankara hattı şehirleri
REGIONS = [
    # Doğu & Kuzeydoğu Anadolu
    "ağrı", "agri", "erzurum", "kars", "iğdır", "igdir", "ardahan",
    "van", "muş", "mus", "bitlis", "hakkari", "erzincan", "tunceli",
    "bingöl", "bingol", "elazığ", "elazig", "malatya",
    # Karadeniz / Kuzeydoğu bağlantısı
    "artvin", "rize", "trabzon", "gümüşhane", "gumushane", "bayburt",
    # Güneydoğu Anadolu
    "gaziantep", "diyarbakır", "diyarbakir", "şanlıurfa", "sanliurfa",
    "batman", "adıyaman", "adiyaman", "mardin", "siirt", "şırnak", "sirnak", "kilis",
    # İç Anadolu bağlantı hattı (Ankara'ya kadar)
    "sivas", "kayseri", "yozgat", "kırıkkale", "kirikkale", "ankara",
    "tokat", "amasya", "çorum", "corum", "kırşehir", "kirsehir", "nevşehir", "nevsehir"
]

TARGETS = [
    {"name": "Renault Clio", "url": "https://www.arabam.com/ikinci-el/otomobil/renault-clio?gear=2&price_max=1200000&take=50"},
    {"name": "Hyundai Bayon", "url": "https://www.arabam.com/ikinci-el/otomobil/hyundai-bayon?gear=2&price_max=1200000&take=50"},
    {"name": "Hyundai i20", "url": "https://www.arabam.com/ikinci-el/otomobil/hyundai-i20?gear=2&price_max=1200000&take=50"},
    {"name": "Kia Stonic", "url": "https://www.arabam.com/ikinci-el/otomobil/kia-stonic?gear=2&price_max=1200000&take=50"},
    {"name": "Fiat Egea", "url": "https://www.arabam.com/ikinci-el/otomobil/fiat-egea?gear=2&price_max=1200000&take=50"},
    {"name": "Fiat Egea Cross", "url": "https://www.arabam.com/ikinci-el/otomobil/fiat-egea-cross?gear=2&price_max=1200000&take=50"}
]

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
            # Gerçek Chrome tarayıcı parmak izi ile 403 engelini atlatma
            res = requests.get(url, impersonate="chrome120", timeout=25)
            print(f"[{model}] Yanıt: {res.status_code}")
            
            if res.status_code != 200:
                continue

            soup = BeautifulSoup(res.text, "html.parser")
            rows = soup.select("tr.listing-list-item")
            print(f"Bulunan ({model}): {len(rows)}")

            for row in rows:
                link_el = row.select_one("td.horizontal-half-paddings a")
                if not link_el:
                    continue

                href = link_el.get("href", "")
                title = clean_text(link_el.get("title") or link_el.text)
                row_id = row.get("id") or href

                price_el = row.select_one("td.listing-price")
                price = clean_text(price_el.text) if price_el else "Fiyat Belirtilmedi"

                loc_el = row.select_one("td.listing-location-city")
                loc = clean_text(loc_el.text) if loc_el else "Türkiye"

                img_el = row.select_one("img")
                img_src = ""
                if img_el:
                    img_src = img_el.get("src") or img_el.get("data-src") or ""
                    img_src = img_src.replace("120x90", "580x435")

                full_url = f"https://www.arabam.com{href}" if not href.startswith("http") else href

                # Bölge filtresi kontrolü
                loc_lower = loc.lower()
                is_in_region = any(city in loc_lower for city in REGIONS)

                if is_in_region:
                    all_rows.append((
                        str(row_id),
                        model,
                        title,
                        price,
                        loc,
                        img_src,
                        "Otomatik",
                        full_url
                    ))
        except Exception as e:
            print(f"Hata ({model}): {e}")

    with sqlite3.connect(DB_FILE) as conn:
        if all_rows:
            conn.executemany("""
                INSERT OR REPLACE INTO listings (id, model_category, title, price, location, image_url, gear_type, url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, all_rows)
            print(f"Tamamlandı! İlgili bölgelerden {len(all_rows)} adet gerçek ilan kaydedildi.")
        else:
            print("İlgili bölgelerde anlık ilan bulunamadı.")

if __name__ == "__main__":
    scrape()
