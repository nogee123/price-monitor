"""Price monitor — collect product data from a paginated catalogue into CSV.

Demo target: books.toscrape.com (a site published explicitly for scraping
practice). Point BASE_URL at a real catalogue and adjust the two parse
functions and the identical pattern monitors competitor prices.

Usage:
    python scraper.py                      # scrape everything
    python scraper.py --max-pages 5        # first 5 pages only
    python scraper.py --out output/books.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://books.toscrape.com/"
USER_AGENT = "price-monitor-demo/1.0 (+contact: your@email.com)"
DELAY_SECONDS = 0.5          # politeness delay between requests
TIMEOUT = 20
RETRIES = 3

RATINGS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


@dataclass
class Product:
    title: str
    price_gbp: float
    rating: int
    in_stock: bool
    url: str


def fetch(url: str, session: requests.Session, retries: int = RETRIES) -> bytes:
    """GET a URL with exponential backoff. Returns raw bytes.

    Bytes, not text: requests often guesses latin-1 on pages that are actually
    UTF-8, which mangles '£' into 'Â£'. Handing bytes to BeautifulSoup lets it
    detect the charset from the document itself. Raises on final failure.
    """
    last: Exception | None = None
    for attempt in range(retries):
        try:
            r = session.get(url, timeout=TIMEOUT)
            r.raise_for_status()
            return r.content
        except requests.RequestException as exc:
            last = exc
            if attempt < retries - 1:
                time.sleep(2 ** attempt)      # 1s, 2s, 4s
    raise RuntimeError(f"failed to fetch {url}: {last}")


def parse_price(text: str) -> float:
    """'£51.77' -> 51.77"""
    return float(text.replace("£", "").replace(",", "").strip())


def parse_stock(text: str) -> bool:
    """'In stock (22 available)' -> True."""
    return "in stock" in " ".join(text.split()).lower()


def parse_products(html: bytes, page_url: str) -> tuple[list[Product], str | None]:
    """Return (products, next_page_url) for one catalogue page.

    Relative links are resolved against `page_url` — the page actually fetched —
    not the crawl's start URL. On a paginated site page N's links are relative
    to page N's own directory, so resolving against the start URL breaks every
    page after the first.
    """
    soup = BeautifulSoup(html, "html.parser")
    products: list[Product] = []

    for card in soup.select("article.product_pod"):
        link = card.select_one("h3 a")
        rating_el = card.select_one("p.star-rating")
        availability = card.select_one("p.instock.availability")

        # star-rating classes look like ['star-rating', 'Three']
        rating = 0
        if rating_el:
            for cls in rating_el.get("class", []):
                if cls in RATINGS:
                    rating = RATINGS[cls]

        products.append(Product(
            title=(link.get("title") or link.get_text(strip=True)) if link else "",
            price_gbp=parse_price(card.select_one("p.price_color").get_text(strip=True)),
            rating=rating,
            in_stock=parse_stock(
                availability.get_text(strip=True) if availability else ""
            ),
            url=urljoin(page_url, link["href"]) if link else "",
        ))

    nxt = soup.select_one("li.next a")
    next_url = urljoin(page_url, nxt["href"]) if nxt else None
    return products, next_url


def scrape(base_url: str, max_pages: int = 0, delay: float = DELAY_SECONDS,
           verbose: bool = True) -> list[Product]:
    """Walk the catalogue from base_url, following 'next' until exhausted."""
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    url: str | None = base_url
    page = 0
    out: list[Product] = []

    while url:
        page += 1
        current = url                      # resolve links against the page fetched
        html = fetch(current, session)
        products, url = parse_products(html, current)
        out.extend(products)
        if verbose:
            print(f"  page {page:>2}: {len(products):>3} products "
                  f"(total {len(out)})")
        if max_pages and page >= max_pages:
            break
        if url:
            time.sleep(delay)

    return out


def write_csv(products: list[Product], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(asdict(products[0]).keys()))
        writer.writeheader()
        writer.writerows(asdict(p) for p in products)


def summarize(products: list[Product]) -> str:
    if not products:
        return "no products collected"
    prices = [p.price_gbp for p in products]
    cheapest = min(products, key=lambda p: p.price_gbp)
    dearest = max(products, key=lambda p: p.price_gbp)
    out_of_stock = sum(1 for p in products if not p.in_stock)
    return (
        f"products collected : {len(products)}\n"
        f"price range        : £{min(prices):.2f} - £{max(prices):.2f}\n"
        f"average price      : £{sum(prices) / len(prices):.2f}\n"
        f"out of stock       : {out_of_stock}\n"
        f"cheapest           : {cheapest.title[:50]} (£{cheapest.price_gbp:.2f})\n"
        f"most expensive     : {dearest.title[:50]} (£{dearest.price_gbp:.2f})"
    )


def main() -> int:
    p = argparse.ArgumentParser(description="Catalogue price scraper")
    p.add_argument("--url", default=BASE_URL, help="catalogue start URL")
    p.add_argument("--max-pages", type=int, default=0, help="0 = all pages")
    p.add_argument("--out", default="output/products.csv")
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args()

    print(f"scraping {args.url}")
    started = time.time()
    products = scrape(args.url, max_pages=args.max_pages,
                      verbose=not args.quiet)
    elapsed = time.time() - started

    if not products:
        print("no products found — has the page structure changed?")
        return 1

    out_path = Path(args.out)
    write_csv(products, out_path)

    print(f"\n{summarize(products)}")
    print(f"\nwrote {out_path}  ({elapsed:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
