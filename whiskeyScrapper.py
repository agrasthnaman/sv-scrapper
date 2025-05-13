import requests
from bs4 import BeautifulSoup
import csv
import time

BASE_URL = "https://www.livcheers.com"
CITY = "bangalore"

# List all the whisky categories you want to scrape
WHISKY_CATEGORIES = [
    "single-malts",
    "world-whisky",
    "made-in-india-whisky",
    "blended-scotch",
    # add more slugs here as needed
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def fetch_whisky_details(
    slug: str, max_retries: int = 3, backoff_factor: float = 1.0
) -> dict:
    """Fetch detail page with retry; extract type, description, tasting notes."""
    url = f"{BASE_URL}/{CITY}/liquor/{slug}"
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            break
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else None
            if status and 500 <= status < 600 and attempt < max_retries:
                wait = backoff_factor * (2 ** (attempt - 1))
                print(
                    f"  ⚠️  {status} for {slug}, retry {attempt}/{max_retries} in {wait}s"
                )
                time.sleep(wait)
                continue
            print(f"  ❌  HTTP Error for {slug}: {e}")
            return {"type": "", "description": "", "tasting_notes": ""}
        except requests.exceptions.RequestException as e:
            if attempt < max_retries:
                wait = backoff_factor * (2 ** (attempt - 1))
                print(
                    f"  ⚠️  Network error for {slug}, retry {attempt}/{max_retries} in {wait}s"
                )
                time.sleep(wait)
                continue
            print(f"  ❌  Network failure for {slug}: {e}")
            return {"type": "", "description": "", "tasting_notes": ""}

    soup = BeautifulSoup(resp.text, "html.parser")

    # --- Type (nested span) ---
    type_val = ""
    type_sel = (
        "body > main"
        " > div:nth-of-type(1)"
        " > div:nth-of-type(2)"
        " > div:nth-of-type(5)"
        " > div > p > span:nth-of-type(2) > span"
    )
    t = soup.select_one(type_sel)
    if t:
        type_val = t.get_text(strip=True)

    # --- Description ---
    d = soup.select_one(
        "body > main > div:nth-of-type(1)"
        " > div:nth-of-type(2)"
        " > div:nth-of-type(6) > p > span:nth-of-type(2)"
    )
    description = d.get_text(strip=True) if d else ""

    # --- Tasting Notes ---
    n = soup.select_one(
        "body > main > div:nth-of-type(1)"
        " > div:nth-of-type(2)"
        " > div:nth-of-type(7) > p > span:nth-of-type(2)"
    )
    tasting_notes = n.get_text(strip=True) if n else ""

    return {
        "type": type_val,
        "description": description,
        "tasting_notes": tasting_notes,
    }


def scrape_category(cat_slug: str) -> list[dict]:
    """Scrape overview cards for a whisky category and enrich with details."""
    url = f"{BASE_URL}/{CITY}/category/{cat_slug}"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    items = []
    cards = soup.find_all("a", href=lambda u: u and u.startswith(f"/{CITY}/liquor/"))

    for card in cards:
        # Image URL
        img_el = card.select_one("div:nth-of-type(1) > img")
        image_url = img_el["src"] if img_el and img_el.has_attr("src") else ""

        # Overview fields
        brand_el = card.select_one(
            "div:nth-of-type(2) > div:nth-of-type(1) > p:nth-of-type(1)"
        )
        name_el = card.select_one("div:nth-of-type(2) > div:nth-of-type(1) > h3")
        size_el = card.select_one(
            "div:nth-of-type(2) > div:nth-of-type(1) > p:nth-of-type(2)"
        )
        rate_el = card.select_one("div:nth-of-type(2) > div:nth-of-type(2) > div")
        price_el = card.select_one("div:nth-of-type(2) > div:nth-of-type(2) > p")

        brand = brand_el.get_text(strip=True) if brand_el else ""
        name = name_el.get_text(strip=True) if name_el else ""
        size = size_el.get_text(strip=True) if size_el else ""
        rating = rate_el.get_text(strip=True) if rate_el else ""
        price = price_el.get_text(strip=True) if price_el else ""

        slug = card["href"].rstrip("/").split("/")[-1]
        details = fetch_whisky_details(slug)

        items.append(
            {
                "region": CITY,
                "category": cat_slug,
                "brand": brand,
                "name": name,
                "slug": slug,
                "size": size,
                "rating": rating,
                "price": price,
                "image_url": image_url,
                **details,
            }
        )

    return items


def main():
    all_items = []
    for category in WHISKY_CATEGORIES:
        print(f"[+] Scraping category: {category}")
        batch = scrape_category(category)
        print(f"    → Found {len(batch)} items")
        all_items.extend(batch)
        time.sleep(1)  # polite pause

    # Write everything to one CSV
    fieldnames = [
        "region",
        "category",
        "brand",
        "name",
        "slug",
        "size",
        "rating",
        "price",
        "image_url",
        "type",
        "description",
        "tasting_notes",
    ]
    with open("livcheers_whisky_p2.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_items)

    print(f"\n✅ Done! {len(all_items)} total items saved to livcheers_whisky_p2.csv")


if __name__ == "__main__":
    main()
