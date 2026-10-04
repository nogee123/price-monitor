"""Offline tests for the scraper's parsing logic (no network).

Run:  pytest test_scraper.py -v
"""
from scraper import parse_price, parse_products, parse_stock

# Minimal fixture mirroring the real catalogue markup.
FIXTURE = b"""
<html><body>
<article class="product_pod">
  <h3><a href="book-a_1/index.html" title="Book A">Book A</a></h3>
  <p class="star-rating Three"></p>
  <p class="price_color">\xc2\xa351.77</p>
  <p class="instock availability">In stock</p>
</article>
<article class="product_pod">
  <h3><a href="book-b_2/index.html" title="Book B">Book B</a></h3>
  <p class="star-rating Five"></p>
  <p class="price_color">\xc2\xa310.00</p>
  <p class="instock availability">In stock (22 available)</p>
</article>
<li class="next"><a href="page-2.html">next</a></li>
</body></html>
"""


def test_parse_price_strips_currency():
    assert parse_price("\u00a351.77") == 51.77
    assert parse_price("\u00a31,234.50") == 1234.50


def test_parse_stock_detects_availability():
    assert parse_stock("In stock") is True
    assert parse_stock("In stock (22 available)") is True
    assert parse_stock("Out of stock") is False


def test_parse_products_extracts_fields():
    products, next_url = parse_products(FIXTURE, "https://example.com/")
    assert len(products) == 2

    a, b = products
    assert a.title == "Book A"
    assert a.price_gbp == 51.77
    assert a.rating == 3
    assert a.in_stock is True
    assert b.rating == 5
    assert b.price_gbp == 10.00


def test_relative_links_resolve_against_page_url():
    """The bug that broke page 3+: links are relative to the CURRENT page."""
    products, next_url = parse_products(FIXTURE, "https://example.com/catalogue/")
    assert products[0].url == "https://example.com/catalogue/book-a_1/index.html"
    assert next_url == "https://example.com/catalogue/page-2.html"


def test_utf8_prices_survive():
    """Guard against the mojibake bug: 'Â£51.77' must not reach float()."""
    products, _ = parse_products(FIXTURE, "https://example.com/")
    assert products[0].price_gbp == 51.77
