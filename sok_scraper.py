#!/usr/bin/env python3
"""Utilities for scraping product prices from the Şok Market web site.

The script offers a small command line interface that can be used to fetch
products either from a concrete category path or the public search endpoint.

Example usage::

    python sok_scraper.py --category atistirmalik
    python sok_scraper.py --search "süt" --pages 2 --format json

The scraper relies on two complementary strategies to retrieve product data.
The first one extracts structured data embedded in Nuxt.js state blobs while
the second one falls back to parsing visible HTML product cards.  The
implementation intentionally keeps all heuristics in dedicated helper
functions so that they are straightforward to update should the web site
change its markup in the future.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, asdict
from html import unescape
from typing import Iterator, List, MutableMapping, Sequence
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup  # type: ignore

BASE_URL = "https://www.sokmarket.com.tr/"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0 Safari/537.36"
)


@dataclass
class Product:
    """Represents a product scraped from the web site."""

    name: str
    price: float
    currency: str | None = None
    unit: str | None = None
    url: str | None = None

    def to_display_row(self) -> Sequence[str]:
        price_part = f"{self.price:.2f}"
        if self.currency:
            price_part = f"{price_part} {self.currency}"
        unit_part = f"/{self.unit}" if self.unit else ""
        return (
            self.name,
            f"{price_part}{unit_part}",
            self.url or "-",
        )


def build_url(category: str | None, search: str | None, page: int) -> str:
    if category:
        suffix = category.strip("/")
        query = f"?sayfa={page}" if page > 1 else ""
        return urljoin(BASE_URL, f"{suffix}{query}")
    if search is None:
        raise ValueError("either category or search must be provided")
    params = {"q": search, "sayfa": page} if page > 1 else {"q": search}
    return urljoin(BASE_URL, f"arama?{urlencode(params)}")


def fetch_html(url: str, *, timeout: int = 20) -> str:
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": BASE_URL,
    }
    request = Request(url, headers=headers)
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
    return raw.decode(response.headers.get_content_charset() or "utf-8", errors="ignore")


def parse_price(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    cleaned = re.sub(r"[^0-9.,]", "", value)
    if not cleaned:
        return None
    if cleaned.count(",") == 1 and cleaned.count(".") == 0:
        cleaned = cleaned.replace(",", ".")
    elif cleaned.count(",") > 1 and cleaned.count(".") == 1:
        cleaned = cleaned.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def iter_dicts(obj: object) -> Iterator[MutableMapping[str, object]]:
    if isinstance(obj, MutableMapping):
        yield obj
        for value in obj.values():
            yield from iter_dicts(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from iter_dicts(item)


def extract_products_from_nuxt_state(soup: BeautifulSoup) -> List[Product]:
    products: List[Product] = []
    pattern = re.compile(r"window\.__NUXT__=", re.IGNORECASE)
    for script in soup.find_all("script"):
        text = script.string or ""
        if not pattern.search(text):
            continue
        try:
            payload = text.split("=", 1)[1].strip()
        except IndexError:
            continue
        payload = payload.rstrip(";")
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            cleaned = payload.replace("undefined", "null")
            try:
                data = json.loads(cleaned)
            except json.JSONDecodeError:
                logging.debug("Unable to decode Nuxt payload")
                continue
        price_keys = {"price", "salesPrice", "discountedPrice", "finalPrice"}
        name_keys = {"name", "productName", "title"}
        url_keys = {"slug", "url", "seoUrl"}
        unit_keys = {"unit", "measurement"}
        currency_keys = {"currency", "currencyCode"}
        for blob in iter_dicts(data):
            name = next((blob[k] for k in name_keys if k in blob), None)
            raw_price = next((blob[k] for k in price_keys if k in blob), None)
            if not name or raw_price is None:
                continue
            price = parse_price(raw_price)
            if price is None:
                continue
            currency = next((blob[k] for k in currency_keys if k in blob), None)
            unit = next((blob[k] for k in unit_keys if k in blob), None)
            raw_url = next((blob[k] for k in url_keys if k in blob), None)
            link = None
            if isinstance(raw_url, str):
                if raw_url.startswith("http"):
                    link = raw_url
                else:
                    link = urljoin(BASE_URL, raw_url.lstrip("/"))
            products.append(
                Product(
                    name=str(name).strip(),
                    price=price,
                    currency=str(currency).strip() if currency else None,
                    unit=str(unit).strip() if unit else None,
                    url=link,
                )
            )
        if products:
            break
    return products


def extract_products_from_cards(soup: BeautifulSoup) -> List[Product]:
    products: List[Product] = []
    card_selectors = [
        "[data-testid='product-card']",
        ".product-card",
        ".product",
    ]
    seen = set()
    for selector in card_selectors:
        for card in soup.select(selector):
            name_tag = (
                card.select_one(".product-title")
                or card.select_one(".prd-title")
                or card.find(attrs={"itemprop": "name"})
                or card.find("h3")
            )
            price_tag = (
                card.select_one(".product-price")
                or card.select_one(".prd-price")
                or card.find(attrs={"itemprop": "price"})
                or card.find(class_=re.compile("price"))
            )
            if not name_tag or not price_tag:
                continue
            name = unescape(name_tag.get_text(strip=True))
            price = parse_price(price_tag.get_text(" ", strip=True))
            if price is None or not name:
                continue
            if name in seen:
                continue
            seen.add(name)
            link_tag = card.find("a", href=True)
            url = urljoin(BASE_URL, link_tag["href"].lstrip("/")) if link_tag else None
            currency = price_tag.get("data-currency") or "₺"
            products.append(Product(name=name, price=price, currency=currency, url=url))
    return products


def scrape_products(category: str | None = None, search: str | None = None, pages: int = 1) -> List[Product]:
    results: List[Product] = []
    for page in range(1, pages + 1):
        url = build_url(category, search, page)
        logging.info("Fetching %s", url)
        html = fetch_html(url)
        soup = BeautifulSoup(html, "html.parser")
        products = extract_products_from_nuxt_state(soup)
        if not products:
            products = extract_products_from_cards(soup)
        if not products:
            logging.warning("No products found on %s", url)
        results.extend(products)
    unique: dict[str, Product] = {}
    for product in results:
        unique.setdefault(product.name, product)
    return list(unique.values())


def format_products(products: Sequence[Product], output_format: str) -> str:
    if output_format == "json":
        return json.dumps([asdict(p) for p in products], ensure_ascii=False, indent=2)
    lines = []
    col_widths = [0, 0, 0]
    rows = [
        ("Ürün", "Fiyat", "Link"),
        ("-" * 20, "-" * 10, "-" * 40),
    ]
    rows.extend(product.to_display_row() for product in products)
    for row in rows:
        for idx, col in enumerate(row):
            col_widths[idx] = max(col_widths[idx], len(col))
    for row in rows:
        padded = [col.ljust(col_widths[idx]) for idx, col in enumerate(row)]
        lines.append("  ".join(padded))
    return "\n".join(lines)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument("--category", help="Category slug, for example 'atistirmalik'.")
    target_group.add_argument("--search", help="Search keyword to query through the public search page.")
    parser.add_argument(
        "--pages",
        type=int,
        default=1,
        help="Number of pages to fetch for the given category/search (default: 1).",
    )
    parser.add_argument(
        "--format",
        choices=("table", "json"),
        default="table",
        help="Output format for the scraped data (default: table).",
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"),
        help="Logging verbosity.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    logging.basicConfig(level=getattr(logging, args.log_level))
    try:
        products = scrape_products(category=args.category, search=args.search, pages=args.pages)
    except Exception as exc:  # pragma: no cover - CLI error reporting
        logging.error("Scraping failed: %s", exc)
        return 1
    if not products:
        logging.warning("No products were found for the requested parameters.")
    output = format_products(products, args.format)
    print(output)
    return 0


if __name__ == "__main__":  # pragma: no cover - script entry point
    raise SystemExit(main())
