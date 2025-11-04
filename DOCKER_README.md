# Docker Deployment Guide

Bu rehber, Browser Test uygulamasını Docker ile nasıl çalıştıracağınızı gösterir.

## Gereksinimler

- Docker Desktop (Windows için)
- Docker Compose

## Kurulum ve Çalıştırma

### 1. Docker Image'ını Oluşturun

```cmd
docker build -t browser-test-app .
```

### 2. Docker Compose ile Çalıştırın

```cmd
docker-compose up -d
```

Bu komut:
- Uygulamayı arka planda çalıştırır
- Port 5000'i açar
- Gerekli volume'ları oluşturur
- Health check'leri etkinleştirir

### 3. Uygulamaya Erişim

Uygulama çalıştığında şu adresten erişebilirsiniz:
```
http://localhost:5000
```

### 4. Logları Görüntüleme

```cmd
docker-compose logs -f browser-test-app
```

### 5. Durdurma

```cmd
docker-compose down
```

## Manuel Docker Çalıştırma (Alternatif)

Eğer docker-compose kullanmak istemiyorsanız:

```cmd
# Image oluşturun
docker build -t browser-test-app .

# Container çalıştırın
docker run -d \
  -p 5000:5000 \
  -v "%cd%\instance:/app/instance" \
  -e FLASK_ENV=production \
  -e SECRET_KEY=your-secret-key-here \
  -e HEADLESS=True \
  --name browser-test-container \
  browser-test-app
```

## Konteyner İçinde Debugging

Eğer sorun yaşarsanız, konteyner içine bağlanabilirsiniz:

```cmd
docker exec -it browser-test-container /bin/bash
```

## Environment Variables

Aşağıdaki ortam değişkenlerini kullanabilirsiniz:

- `FLASK_ENV`: production veya development (varsayılan: production)
- `SECRET_KEY`: Flask uygulaması için güvenlik anahtarı
- `HEADLESS`: True/False - Tarayıcı headless modunda çalışsın mı?
- `DATABASE_URL`: Veritabanı bağlantı URL'si

## Volume'lar

- `./instance:/app/instance` - Veritabanı dosyaları
- `./logs:/app/logs` - Uygulama logları

## Ports

- `5000:5000` - Flask uygulaması

## Troubleshooting

### Konteyner başlamıyor
1. Logları kontrol edin: `docker-compose logs browser-test-app`
2. Port 5000'in kullanımda olmadığından emin olun
3. Docker Desktop'un çalıştığından emin olun

### Tarayıcı automation çalışmıyor
1. X11 server'ın düzgün kurulduğunu kontrol edin
2. Chrome/ChromeDriver sürümlerinin uyumlu olduğunu kontrol edin
3. HEADLESS=True ayarının doğru olduğunu kontrol edin

### Veritabanı sorunları
1. `./instance` klasörünün yazma izinleri olduğunu kontrol edin
2. Veritabanı dosyasının corrupted olmadığını kontrol edin