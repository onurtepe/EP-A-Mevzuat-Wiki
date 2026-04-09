"""
scraper_check.py
================
GitHub Actions'ta çalışır. Selenium gerektirmez.
EPİAŞ mevzuat sayfalarını tarar, manifest.json ile karşılaştırır,
yeni belge varsa stdout'a özel format ile yazar.

GitHub Actions workflow bu çıktıyı parse edip Issue açar.
"""

import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE_DIR  = Path(__file__).resolve().parent
MANIFEST  = BASE_DIR / "manifest.json"
MULGA     = "Mülga/Önceki Versiyonlar"

SOURCE_PAGES = {
    "kanunlar":           "https://www.epias.com.tr/kanunlar/",
    "yonetmelikler":      "https://www.epias.com.tr/yonetmelikler/",
    "kurul-kararlari":    "https://www.epias.com.tr/kurul-kararlari/",
    "yontem-prosedurler": "https://www.epias.com.tr/yontem-prosedurler/",
}

DOWNLOADABLE = {".pdf", ".doc", ".docx"}
EXTERNAL_DOMAINS = {"mevzuat.gov.tr", "resmigazete.gov.tr"}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; EPIASWikiBot/1.0)"
    )
}

KATEGORI_ETIKET = {
    "kanunlar":           "Kanun",
    "yonetmelikler":      "Yönetmelik",
    "kurul-kararlari":    "Kurul Kararı",
    "yontem-prosedurler": "Yöntem/Prosedür",
}


def domain_of(url):
    return urlparse(url).netloc.removeprefix("www.")


def extract_links(category, page_url):
    try:
        resp = requests.get(page_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"  HATA: {page_url} — {e}", file=sys.stderr)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    content = soup.find("div", class_="entry-content") or soup.find("main") or soup.body

    links = []
    skip = False
    seen = set()

    for tag in content.find_all(["strong", "p", "li", "h2", "h3", "h4"]):
        text = tag.get_text(strip=True)
        if category == "yontem-prosedurler" and MULGA in text:
            skip = True
        if skip:
            continue
        for a in tag.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith("#") or href.startswith("javascript"):
                continue
            url = urljoin(page_url, href)
            if url in seen:
                continue
            seen.add(url)
            ext = Path(urlparse(url).path).suffix.lower()
            dom = domain_of(url)
            if ext in DOWNLOADABLE or dom in EXTERNAL_DOMAINS:
                title = a.get_text(strip=True) or Path(urlparse(url).path).name
                links.append({"title": title, "url": url, "category": category})

    return links


def main():
    # manifest.json yoksa (ilk çalıştırma) tüm belgeler "yeni" sayılır
    if MANIFEST.exists():
        with open(MANIFEST, encoding="utf-8") as f:
            manifest = json.load(f)
        bilinen_urllar = set(manifest.keys())
    else:
        manifest = {}
        bilinen_urllar = set()

    yeni_belgeler = []

    for category, page_url in SOURCE_PAGES.items():
        links = extract_links(category, page_url)
        for link in links:
            if link["url"] not in bilinen_urllar:
                yeni_belgeler.append(link)

    if yeni_belgeler:
        print(f"YENI_BELGE:{len(yeni_belgeler)}")
        print()
        for b in yeni_belgeler:
            etiket = KATEGORI_ETIKET.get(b["category"], b["category"])
            print(f"- [{etiket}] {b['title']}")
            print(f"  {b['url']}")
    else:
        print("Yeni mevzuat tespit edilmedi.")

    # manifest.json'u güncelle (sadece yeni URL'leri ekle, var olanları korur)
    if yeni_belgeler and MANIFEST.exists():
        from datetime import datetime
        for b in yeni_belgeler:
            manifest[b["url"]] = {
                "category":     b["category"],
                "title":        b["title"],
                "url":          b["url"],
                "type":         "external_html" if domain_of(b["url"]) in EXTERNAL_DOMAINS else "download",
                "local_path":   None,
                "status":       "pending",
                "last_checked": datetime.now().isoformat(),
            }
        with open(MANIFEST, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
