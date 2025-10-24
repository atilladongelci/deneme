# deneme

Bu depo, Şok Market web sitesindeki ürünlerin fiyatlarını çekmeye yönelik basit
bir web scraping aracını içerir.

## Kurulum

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Kullanım

Bir kategori içindeki ürünleri listelemek:

```bash
python sok_scraper.py --category atistirmalik
```

Belirli bir anahtar kelime ile arama yapmak:

```bash
python sok_scraper.py --search "süt" --pages 2 --format json
```

`--format json` çıktıyı JSON formatında döndürürken, varsayılan `table` seçeneği
tablo benzeri okunabilir bir çıktı üretir.
