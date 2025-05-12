import requests
from bs4 import BeautifulSoup
import csv
import time

BASE_URL = "https://www.livcheers.com"
CITY = "bangalore"

CATEGORIES = [
    "gin",
    # "rum", "champagne", "vodka", ...
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def fetch_product_details(slug: str) -> dict:
    """Fetch image_url, botanicals, description, tasting_notes, and type."""
    url = f"{BASE_URL}/{CITY}/liquor/{slug}"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # 1) Image URL: /html/body/main/div[1]/div[1]/img
    image_url = ""
    img_tag = soup.select_one(
        "body > main > div:nth-of-type(1) > div:nth-of-type(1) > img"
    )
    if img_tag and img_tag.has_attr("src"):
        image_url = img_tag["src"]

    # 2) Botanicals: /html/body/main/div[1]/div[2]/div[5]/div[2]/p
    botanicals = ""
    bot_p = soup.select_one(
        "body > main > div:nth-of-type(1) > div:nth-of-type(2) > div:nth-of-type(5) > div:nth-of-type(2) > p"
    )
    if bot_p:
        botanicals = bot_p.get_text(strip=True)

    # 3) Description: /html/body/main/div[1]/div[2]/div[6]/p/span[2]
    description = ""
    desc_span = soup.select_one(
        "body > main > div:nth-of-type(1) > div:nth-of-type(2) > div:nth-of-type(6) > p > span:nth-of-type(2)"
    )
    if desc_span:
        description = desc_span.get_text(strip=True)

    # 4) Tasting Notes: /html/body/main/div[1]/div[2]/div[7]/p/span[2]
    tasting_notes = ""
    notes_span = soup.select_one(
        "body > main > div:nth-of-type(1) > div:nth-of-type(2) > div:nth-of-type(7) > p > span:nth-of-type(2)"
    )
    if notes_span:
        tasting_notes = notes_span.get_text(strip=True)

    # 5) Type: label “Type:” → next sibling span
    type_val = ""
    type_label = soup.find("span", string="Type:")
    if type_label:
        sib = type_label.find_next_sibling("span")
        if sib:
            type_val = sib.get_text(strip=True)

    return {
        "image_url": image_url,
        "botanicals": botanicals,
        "description": description,
        "tasting_notes": tasting_notes,
        "type": type_val,
    }


def scrape_category(cat_slug: str) -> list[dict]:
    """Scrape the category overview and enrich with detailed page data."""
    url = f"{BASE_URL}/{CITY}/category/{cat_slug}"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    items = []
    cards = soup.find_all("a", href=lambda u: u and u.startswith(f"/{CITY}/liquor/"))

    for card in cards:
        # Overview fields
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

        # Fetch detail page data
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
                **details,
            }
        )

    return items


def main():
    all_products = []
    for cat in CATEGORIES:
        print(f"[+] Scraping {cat}…", end=" ")
        try:
            batch = scrape_category(cat)
            print(f"found {len(batch)} items")
            all_products.extend(batch)
        except Exception as e:
            print("error:", e)
        time.sleep(1)

    # Write to CSV
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
        "image_url",
        "type",
        "botanicals",
        "description",
        "tasting_notes",
    ]
    with open("livcheers_detailed_p12.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_products)

    print(f"\n✅ Done! {len(all_products)} products saved to livcheers_detailed_p12.csv")


if __name__ == "__main__":
    main()
