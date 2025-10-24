# deneme

deneme

## Web scraping aracı

`https://www.a101.com.tr/kapida/` adresindeki ürünleri kategori, ürün adı ve fiyat
bilgileriyle listelemek için `scrape_a101.py` betiğini kullanabilirsiniz.

```bash
python scrape_a101.py
```

Betik çıktıyı tablo halinde yazdırır. JSON formatında sonuç almak için `--json`
bayrağını kullanabilirsiniz:

```bash
python scrape_a101.py --json
```

Betik, sayfadaki `window.__NUXT__` içerisinde yer alan verileri kullanır. Eğer
web sitesi yapısı değişirse, betik hatayla sonlanabilir. İnternete erişim
olmayan ortamlarda betik çalıştırılamaz.

### Testler

```bash
python -m unittest discover -s tests
```
