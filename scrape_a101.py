"""Utility to scrape product categories, names, and prices from A101 Kapida."""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, List, Optional, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


NUXT_STATE_PATTERN = re.compile(r"window\.__NUXT__\s*=\s*(\{.*?\})\s*;", re.DOTALL)


@dataclass(frozen=True)
class Product:
    category: str
    name: str
    price: str

    def as_row(self) -> Sequence[str]:
        return (self.category, self.name, self.price)


class ScrapingError(RuntimeError):
    """Raised when the page cannot be scraped."""


# Keys that frequently describe product metadata on the web site.
NAME_KEYS = ("productName", "name", "title", "displayName")
PRICE_KEYS = ("price", "priceText", "priceValue", "finalPrice", "formattedPrice")
CATEGORY_KEYS = (
    "categoryName",
    "category",
    "categoryTitle",
    "parentCategoryName",
    "breadcrumbTitle",
)


def download_html(url: str, *, timeout: float = 30.0) -> str:
    """Download the raw HTML content from ``url``.

    Parameters
    ----------
    url:
        The URL that should be downloaded.
    timeout:
        Number of seconds to wait for the server to respond.

    Returns
    -------
    str
        The decoded HTML payload.

    Raises
    ------
    ScrapingError
        If the network request fails.
    """

    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})

    try:
        with urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset("utf-8")
            return response.read().decode(charset)
    except (HTTPError, URLError) as exc:
        raise ScrapingError(f"Failed to download '{url}': {exc}") from exc


def extract_nuxt_state(html: str) -> Dict:
    """Extract the JSON payload assigned to ``window.__NUXT__``.

    The Kapida web site hydrates its pages by embedding a Nuxt state
    object in ``window.__NUXT__``.  This helper locates the first
    occurrence of that state block and parses it as JSON.

    Parameters
    ----------
    html:
        The raw HTML of the page.

    Returns
    -------
    dict
        Parsed JSON data structure.

    Raises
    ------
    ScrapingError
        If the expected script block cannot be located or the JSON
        payload is invalid.
    """

    match = NUXT_STATE_PATTERN.search(html)
    if not match:
        raise ScrapingError("The page does not contain a window.__NUXT__ block.")

    payload = match.group(1)

    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ScrapingError("Unable to parse the Nuxt state JSON payload.") from exc


def _best_value(data: Dict[str, object], keys: Sequence[str]) -> Optional[str]:
    for key in keys:
        value = data.get(key)
        if isinstance(value, (str, int, float)):
            return str(value)
    return None


def collect_products(data: object) -> List[Product]:
    """Traverse *data* and extract product entries.

    Parameters
    ----------
    data:
        The parsed Nuxt state.  The function iterates over the nested
        structure recursively and yields all objects that look like
        product definitions.

    Returns
    -------
    list of :class:`Product`
    """

    collected: Dict[Product, None] = {}

    def _find_nested_category(node: object) -> Optional[str]:
        if isinstance(node, dict):
            candidate = _best_value(node, CATEGORY_KEYS)
            if candidate:
                return candidate
            for value in node.values():
                nested = _find_nested_category(value)
                if nested:
                    return nested
        elif isinstance(node, list):
            for item in node:
                nested = _find_nested_category(item)
                if nested:
                    return nested
        return None

    def _traverse(node: object, context_category: Optional[str]) -> Iterator[Product]:
        if isinstance(node, dict):
            category = context_category
            candidate_category = _best_value(node, CATEGORY_KEYS)
            if not candidate_category:
                for key, value in node.items():
                    if isinstance(key, str) and key.lower().startswith("categor"):
                        candidate_category = _find_nested_category(value)
                        if candidate_category:
                            break
            if candidate_category:
                category = candidate_category

            name = _best_value(node, NAME_KEYS)
            price = _best_value(node, PRICE_KEYS)

            if name and price:
                yield Product(category=category or "Belirtilmemiş", name=name, price=price)

            for value in node.values():
                yield from _traverse(value, category)

        elif isinstance(node, list):
            for item in node:
                yield from _traverse(item, context_category)

    for product in _traverse(data, None):
        collected.setdefault(product, None)

    return list(collected.keys())


def format_products(products: Iterable[Product]) -> str:
    """Return a pretty-printed table of ``products``."""

    rows = [Product("Kategori", "Ürün", "Fiyat").as_row()]
    rows.extend(product.as_row() for product in products)

    # Determine column widths
    widths = [max(len(row[idx]) for row in rows) for idx in range(3)]

    def _format(row: Sequence[str]) -> str:
        return " | ".join(col.ljust(widths[idx]) for idx, col in enumerate(row))

    separator = "-+-".join("-" * width for width in widths)

    formatted_rows = [_format(rows[0]), separator]
    formatted_rows.extend(_format(row) for row in rows[1:])
    return "\n".join(formatted_rows)


def scrape(url: str) -> List[Product]:
    html = download_html(url)
    state = extract_nuxt_state(html)
    return collect_products(state)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Scrape A101 Kapıda products")
    parser.add_argument(
        "url",
        nargs="?",
        default="https://www.a101.com.tr/kapida/",
        help="Page URL to scrape (defaults to the Kapida landing page)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output the scraped products as JSON instead of a table.",
    )

    args = parser.parse_args(argv)

    products = scrape(args.url)

    if args.json:
        serialised = [product.__dict__ for product in products]
        print(json.dumps(serialised, ensure_ascii=False, indent=2))
    else:
        print(format_products(products))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
