import requests
from bs4 import BeautifulSoup
import csv
import time
import re

BASE_URL = "https://www.livcheers.com"
CITY = "bangalore"

CATEGORIES = [
    "gin",
    # "rum",
    # "champagne",
    # "vodka",
    # "ready-to-drink",
    # "beers",
    # "sake",
    # "liqueurs",
    # "brandy",
    # "tequila",
    # "sparkling-wine",
    # "rose-wine",
    # "red-wine",
    # "white-wine",
    # "single-malts",
    # "world-whisky",
    # "made-in-india-whisky",
    # "blended-scotch",
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def fetch_product_details(slug: str) -> dict:
    """Fetch type, botanicals, description, and tasting notes using precise CSS paths."""
    url = f"{BASE_URL}/{CITY}/liquor/{slug}"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # --- Type (unchanged) ---
    type_val = ""
    tl = soup.find("span", string="Type:")
    if tl and (sib := tl.find_next_sibling("span")):
        type_val = sib.get_text(strip=True)

    # --- Botanicals (4th div → fallback to 5th) ---
    botanicals = ""
    for idx in (4, 5):
        sel = (
            f"body > main > div:nth-of-type(2) > div:nth-of-type(2) "
            f"> div:nth-of-type({idx}) > div:nth-of-type(2) > p > span:nth-of-type(2)"
        )
        node = soup.select_one(sel)
        if node and node.get_text(strip=True):
            botanicals = node.get_text(strip=True)
            break

    # --- Description (6th div block) ---
    desc = ""
    desc_sel = (
        "body > main > div:nth-of-type(2) > div:nth-of-type(2) "
        "> div:nth-of-type(6) > p > span:nth-of-type(2)"
    )
    if (d := soup.select_one(desc_sel)) and d.get_text(strip=True):
        desc = d.get_text(strip=True)

    # --- Tasting Notes (7th div block) ---
    notes = ""
    notes_sel = (
        "body > main > div:nth-of-type(2) > div:nth-of-type(2) "
        "> div:nth-of-type(7) > p > span:nth-of-type(2)"
    )
    if (n := soup.select_one(notes_sel)) and n.get_text(strip=True):
        notes = n.get_text(strip=True)

    return {
        "type": type_val,
        "botanicals": botanicals,
        "description": desc,
        "tasting_notes": notes,
    }


def scrape_category(cat_slug: str) -> list[dict]:
    """Scrape overview cards and enrich with detailed fields."""
    url = f"{BASE_URL}/{CITY}/category/{cat_slug}"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    items = []

    for card in soup.find_all(
        "a", href=lambda u: u and u.startswith(f"/{CITY}/liquor/")
    ):
        brand_el = card.find("p", class_=lambda c: c and "text-[#007CF5]" in c)
        name_el = card.find("h3")
        size_el = card.find("p", class_=lambda c: c and "text-[#9FA5A7]" in c)
        rating_el = card.find(
            "p", class_=lambda c: c and "text-white" in c and "font-semibold" in c
        )
        price_el = card.find(
            "p", class_=lambda c: c and "text-xs" in c and "font-semibold" in c
        )
        compound_el = card.find(
            "p", class_=lambda c: c and "line-clamp-1" in c and "text-left" in c
        )

        name = name_el.get_text(strip=True) if name_el else ""
        slug = card["href"].rstrip("/").split("/")[-1]
        details = fetch_product_details(slug)

        items.append(
            {
                "region": CITY,
                "category": cat_slug,
                "brand": brand_el.get_text(strip=True) if brand_el else "",
                "name": name,
                "slug": slug,
                "size": size_el.get_text(strip=True) if size_el else "",
                "rating": rating_el.get_text(strip=True) if rating_el else "",
                "price": price_el.get_text(strip=True) if price_el else "",
                "compound": compound_el.get_text(strip=True) if compound_el else "",
                "type": details["type"],
                "botanicals": details["botanicals"],
                "description": details["description"],
                "tasting_notes": details["tasting_notes"],
            }
        )

    return items


def main():
    all_products = []
    for cat in CATEGORIES:
        print(f"[+] Scraping {cat}…", end=" ")
        try:
            prods = scrape_category(cat)
            print(f"found {len(prods)} items")
            all_products.extend(prods)
        except Exception as e:
            print("error:", e)
        time.sleep(1)

    # write CSV
    fieldnames = [
        "region",
        "category",
        "brand",
        "name",
        "slug",
        "size",
        "rating",
        "price",
        "compound",
        "type",
        "botanicals",
        "description",
        "tasting_notes",
    ]
    with open(
        "livcheers_detailed_p7.csv", "w", newline="", encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_products)

    print(
        f"\n✅ Done! {len(all_products)} total products saved to livcheers_detailed_p7.csv"
    )


if __name__ == "__main__":
    main()
