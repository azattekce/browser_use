# Browser Test Uygulaması - Çalıştırma Rehberi

Bu uygulama web sitelerinde otomatik testler yapmak için geliştirilmiş bir Flask uygulamasıdır.

## Kurulum Seçenekleri

### Seçenek 1: Yerel Kurulum (Önerilen)

#### Gereksinimler
- Python 3.8 veya üzeri
- Google Chrome tarayıcısı
- Git (opsiyonel)

#### Kurulum Adımları

1. **Proje klasörüne gidin:**
   ```cmd
   cd /d "c:\zattekce\Projects\workplace\browser-use_new"
   ```

2. **Sanal ortam oluşturun (önerilen):**
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Gerekli paketleri yükleyin:**
   ```cmd
   pip install -r requirements.txt
   ```

4. **Uygulamayı çalıştırın:**
   ```cmd
   python app.py
   ```

5. **Tarayıcıda açın:**
   http://localhost:5000

### Seçenek 2: Docker ile Kurulum

Docker Desktop kurulu ise:

1. **Docker image oluşturun:**
   ```cmd
   docker build -t browser-test-app .
   ```

2. **Docker Compose ile çalıştırın:**
   ```cmd
   docker-compose up -d
   ```

3. **Tarayıcıda açın:**
   http://localhost:5000

Detaylı Docker kurulum bilgisi için `DOCKER_README.md` dosyasını inceleyin.

## Kullanım

1. **Ana sayfa:** Test oluşturma formu
2. **Test Geçmişi:** Daha önce yapılan testleri görüntüleme
3. **Test Sonuçları:** Detaylı test sonuçları ve tekrar çalıştırma

### Test Oluşturma

1. Ana sayfada formu doldurun:
   - Proje Adı
   - Test URL'i
   - Test Senaryosu (ne yapılacağını açıklayın)

2. "Test Başlat" butonuna tıklayın

3. Test sonuçlarını bekleyin

### Test Tekrarı

- Test sonucu sayfasından "Tekrar Çalıştır" butonu ile
- Test geçmişinden "Tekrar Çalıştır" butonu ile

## Özellikler

- ✅ Gerçek tarayıcı otomasyonu (Chrome)
- ✅ Modern, profesyonel arayüz
- ✅ Test geçmişi ve sonuçları
- ✅ Test tekrarı özelliği
- ✅ Responsive tasarım
- ✅ Modal dialog'lar
- ✅ Toast bildirimleri
- ✅ Docker desteği

## Sorun Giderme

### Yaygın Sorunlar

1. **Chrome bulunamıyor hatası:**
   - Google Chrome'un kurulu olduğundan emin olun
   - Chrome'un PATH'e ekli olduğunu kontrol edin

2. **ModuleNotFoundError:**
   - requirements.txt'deki tüm paketlerin yüklendiğini kontrol edin
   - Sanal ortamın aktif olduğunu kontrol edin

3. **Port zaten kullanımda:**
   - 5000 portunu kullanan başka uygulamayı kapatın
   - Farklı port kullanmak için app.py'de değişiklik yapın

4. **Veritabanı hatası:**
   - instance/ klasörünün yazma izinleri olduğunu kontrol edin
   - SQLite veritabanı dosyasını silin, otomatik yeniden oluşturulur

### Debug Modu

Geliştirme sırasında debug modu için:

```cmd
set FLASK_DEBUG=1
python app.py
```

### Log Dosyaları

Uygulama logları şu konumlarda:
- Konsol çıktısı
- logs/ klasörü (oluşturulursa)

## Teknoloji Stack

- **Backend:** Flask 2.3.3
- **Frontend:** Bootstrap 5, JavaScript
- **Database:** SQLite
- **Browser Automation:** browser-use 0.8.0+
- **Containerization:** Docker (opsiyonel)

## Geliştirme

Kod değişiklikleri için:

1. Sanal ortamı aktifleştirin
2. Değişiklikleri yapın
3. Flask debug modu ile test edin
4. Production için Docker build edin

## Lisans

Bu proje kişisel kullanım için geliştirilmiştir.