# Catalogue Price Monitor

A Python scraper that walks a paginated product catalogue, extracts structured
data from every listing, and writes it to a clean CSV — with a summary of price
range, averages, and stock status.

**Business use case:** competitor price monitoring. Point it at a supplier's or
competitor's catalogue, run it on a schedule, and see exactly what moved.

> Demo target: [books.toscrape.com](https://books.toscrape.com/), a sandbox site
> published specifically for scraping practice. The pattern transfers directly to
> real catalogues — change `BASE_URL` and the two parse functions.

---

## Quick start

Set up an isolated environment first — this keeps the project's libraries out of
your global Python instead of polluting it:

```bash
uv venv                             # creates a project-local .venv folder
uv pip install -r requirements.txt  # installs requests, BeautifulSoup4, pytest
```

No `uv`? Plain Python works too:

```bash
python -m venv .venv
.venv\Scripts\activate              # Windows
# source .venv/bin/activate         # macOS / Linux
pip install -r requirements.txt
```

Then run it:

```bash
python scraper.py                      # whole catalogue (~45s)
python scraper.py --max-pages 5        # first 5 pages
python scraper.py --out data/books.csv
```

Run the tests with `pytest test_scraper.py` (they're offline — no network needed).

## Sample output

```
scraping https://books.toscrape.com/
  page  1:  20 products (total 20)
  page  2:  20 products (total 40)
  ...
  page 50:  20 products (total 1000)

products collected : 1000
price range        : £10.00 - £59.99
average price      : £35.07
out of stock       : 0
cheapest           : An Abundance of Katherines (£10.00)
most expensive     : The Perfect Play (Play by Play #1) (£59.99)
```

`output/products.csv`:

| title | price_gbp | rating | in_stock | url |
|---|---|---|---|---|
| A Light in the Attic | 51.77 | 3 | True | https://books.toscrape.com/catalogue/… |
| Tipping the Velvet | 53.74 | 1 | True | https://books.toscrape.com/catalogue/… |

## How it works

1. **`fetch()`** — GET with configurable retries and exponential backoff (1s → 2s → 4s), so a single timeout doesn't kill a 50-page crawl.
2. **`parse_products()`** — extracts title, price, star rating, stock status and absolute URL from each listing; finds the "next page" link.
3. **`scrape()`** — follows pagination until exhausted or `--max-pages` is hit, with a politeness delay between requests.
4. **`write_csv()` / `summarize()`** — writes a clean CSV and prints a price summary.

## What this demonstrates

Deliberately covered, because these are the things that break real scrapers:

- **Pagination** — follows "next" links until the catalogue ends
- **Relative URL resolution** — links are resolved against *the page fetched*, not the crawl's start URL. This is the classic bug that makes page 3 onwards 404.
- **Character encoding** — the response is parsed as **bytes**, letting the HTML parser detect the charset. `requests` frequently guesses latin-1 on UTF-8 pages, turning `£51.77` into `Â51.77` and crashing the price parser.
- **Robustness** — retries with backoff, a timeout on every request, and an identifiable User-Agent
- **Politeness** — rate limiting between requests rather than hammering a server
- **Clean output** — typed dataclass, CSV export, human-readable summary
- **Tests** — 5 offline tests covering the parsing logic, including a regression test for each bug above (`pytest test_scraper.py`)

## Extending it into a monitoring service

The pieces a paid version adds on top:

- Store each run in SQLite and **diff against yesterday** → report only what changed
- Schedule it (cron / Task Scheduler) and deliver the diff by email or Slack
- Alert on thresholds ("notify me if any price drops >10%")

---

Built with Python, `requests`, `BeautifulSoup4`. MIT licensed.
