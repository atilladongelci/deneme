import json
import textwrap
import unittest

from scrape_a101 import (
    Product,
    collect_products,
    extract_nuxt_state,
    format_products,
)


SAMPLE_HTML = textwrap.dedent(
    """
    <html>
      <head>
        <script>
        window.__NUXT__ = {"data": [{
          "categories": {"categoryName": "Meyveler"},
          "products": {
            "items": [
              {"productName": "Elma", "price": "19,95 TL", "categoryName": "Meyveler"},
              {"productName": "Peynir", "finalPrice": 42.5, "category": "Süt"},
              {"name": "Ekmek", "priceText": "5,00 TL"}
            ]
          }
        }]};
        </script>
      </head>
    </html>
    """
)


class TestExtractNuxtState(unittest.TestCase):
    def test_extracts_json_payload(self) -> None:
        state = extract_nuxt_state(SAMPLE_HTML)
        self.assertIn("data", state)

    def test_collect_products(self) -> None:
        state = json.loads('{"data": [{"foo": 1}]}')
        products = collect_products(state)
        self.assertEqual(products, [])


class TestCollectProducts(unittest.TestCase):
    def test_detects_products_and_categories(self) -> None:
        state = extract_nuxt_state(SAMPLE_HTML)
        products = collect_products(state)
        self.assertCountEqual(
            products,
            [
                Product(category="Meyveler", name="Elma", price="19,95 TL"),
                Product(category="Süt", name="Peynir", price="42.5"),
                Product(category="Meyveler", name="Ekmek", price="5,00 TL"),
            ],
        )


class TestFormatProducts(unittest.TestCase):
    def test_generates_table(self) -> None:
        table = format_products(
            [
                Product(category="Kategori", name="Ürün", price="Fiyat"),
                Product(category="Meyve", name="Elma", price="19,95 TL"),
            ]
        )
        self.assertIn("Meyve", table)
        self.assertIn("Elma", table)


if __name__ == "__main__":
    unittest.main()
