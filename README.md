# Berber Rezervasyon Aracı

Bu proje, berberler için SMS tabanlı bir rezervasyon akışı sağlayan basit bir Flask uygulamasıdır. Müşteri belirlenen numaraya mesaj attığında yapay zekâ destekli bir asistanla görüşür, uygun gün ve saat belirlendikten sonra rezervasyon onayı gönderilir ve randevudan bir gün önce hatırlatma mesajı yollanır.

## Özellikler

- SMS üzerinden Türkçe konuşan rezervasyon asistanı
- Gün ve saat bilgilerini toplayarak otomatik onay gönderimi
- Rezervasyondan 24 saat önce otomatik hatırlatma mesajı
- JSON tabanlı kalıcı saklama
- Flask ile webhook entegrasyonu

## Kurulum

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Çalıştırma

```bash
export FLASK_APP=app.py
flask run --host 0.0.0.0 --port 5000
```

Uygulama aşağıdaki HTTP uç noktalarını sağlar:

- `GET /health`: Sağlık kontrolü.
- `POST /sms`: SMS sağlayıcınızdan gelecek webhook. JSON gövdesi `{"from": "+905551112233", "message": "Merhaba"}` formatında olmalıdır.
- `GET /reservations`: Kaydedilen tüm rezervasyonları listeler.

Gerçek SMS gönderimi için `ConsoleMessageClient` yerine Twilio gibi bir servisle entegre olacak bir istemci yazabilirsiniz.

## Geliştirme Notları

- Rezervasyon hatırlatmaları `APScheduler` kullanılarak planlanır. Uygulama durdurulursa `data/reservations.json` dosyası sayesinde kayıtlar korunur ve tekrar başlatıldığında hatırlatıcılar yeniden planlanır.
- Tarih formatı gün/saat sorularında `gg.aa.yyyy` ve `gg/aa/yyyy` kalıplarını destekler.
