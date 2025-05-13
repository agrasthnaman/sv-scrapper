import requests
from bs4 import BeautifulSoup
import csv
import time

BASE_URL = "https://www.livcheers.com"
CITY = "bangalore"

# List all the wine categories you want to scrape
WINE_CATEGORIES = [
    "sparkling-wine",
    "rose-wine",
    "red-wine",
    "white-wine",
    # add more slugs here as needed
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


import requests
from bs4 import BeautifulSoup
import csv
import time

BASE_URL = "https://www.livcheers.com"
CITY = "bangalore"

# List all the wine categories you want to scrape
WINE_CATEGORIES = [
    "sparkling-wine",
    "rose-wine",
    "red-wine",
    "white-wine",
    # add more slugs here as needed
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def fetch_wine_details(
    slug: str, max_retries: int = 3, backoff_factor: float = 1.0
) -> dict:
    """Fetch detail page with retry on 5xx errors; on failure, return empty fields."""
    url = f"{BASE_URL}/{CITY}/liquor/{slug}"
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            break  # success
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else None
            # retry on server errors (5xx), else give up immediately
            if status and 500 <= status < 600 and attempt < max_retries:
                wait = backoff_factor * (2 ** (attempt - 1))
                print(
                    f"  ⚠️  Got {status} for {slug}, retrying in {wait}s… (attempt {attempt})"
                )
                time.sleep(wait)
                continue
            else:
                print(f"  ❌  Failed to fetch details for {slug}: {e}")
                return {"type": "", "description": "", "tasting_notes": ""}
        except requests.exceptions.RequestException as e:
            # network error or timeout
            if attempt < max_retries:
                wait = backoff_factor * (2 ** (attempt - 1))
                print(
                    f"  ⚠️  Network error for {slug}, retrying in {wait}s… (attempt {attempt})"
                )
                time.sleep(wait)
                continue
            else:
                print(f"  ❌  Network failure for {slug}: {e}")
                return {"type": "", "description": "", "tasting_notes": ""}

    # If we break out, resp is good
    soup = BeautifulSoup(resp.text, "html.parser")

    # now extract fields as before…
    t = soup.select_one(
        "body > main > div:nth-of-type(1) > div:nth-of-type(2) "
        "> div:nth-of-type(5) > p > span:nth-of-type(2)"
    )
    type_val = t.get_text(strip=True) if t else ""

    d = soup.select_one(
        "body > main > div:nth-of-type(1) > div:nth-of-type(2) "
        "> div:nth-of-type(6) > p > span:nth-of-type(2)"
    )
    description = d.get_text(strip=True) if d else ""

    n = soup.select_one(
        "body > main > div:nth-of-type(1) > div:nth-of-type(2) "
        "> div:nth-of-type(7) > p > span:nth-of-type(2)"
    )
    tasting_notes = n.get_text(strip=True) if n else ""

    return {
        "type": type_val,
        "description": description,
        "tasting_notes": tasting_notes,
    }


def scrape_category(cat_slug: str) -> list[dict]:
    """Scrape overview cards for a given wine category and return enriched rows."""
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
        details = fetch_wine_details(slug)

        # Build the row dict, including the category
        row = {
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
        items.append(row)

    return items


def main():
    all_wines = []
    for category in WINE_CATEGORIES:
        print(f"[+] Scraping category: {category}")
        wines = scrape_category(category)
        print(f"    → Found {len(wines)} items")
        all_wines.extend(wines)
        time.sleep(1)  # polite pause

    # Write a single CSV containing all categories
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
    with open("livcheers_wines_p3.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_wines)

    print(f"\n✅ Done! {len(all_wines)} total items saved to livcheers_wines_p3.csv")


if __name__ == "__main__":
    main()
