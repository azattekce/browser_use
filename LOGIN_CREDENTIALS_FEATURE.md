# Proje Giriş Bilgileri Özelliği - Dokümantasyon

## Özellik Özeti
Projeler artık otomatik giriş bilgileri saklayabilir ve test sırasında bu bilgiler otomatik olarak kullanılabilir.

## Yapılan Değişiklikler

### 1. Veritabanı Şeması Güncellemeleri
- `Project` tablosuna yeni sütunlar eklendi:
  - `login_enabled`: BOOLEAN (varsayılan: false)
  - `login_username`: VARCHAR(255) 
  - `login_password`: TEXT (şifrelenmiş)

### 2. Model Güncellemeleri (`app/models.py`)
- `Project` modeline yeni alanlar eklendi
- Şifreleme/şifre çözme metodları eklendi:
  - `_get_encryption_key()`: Güvenli şifreleme anahtarı üretimi
  - `set_login_credentials()`: Kullanıcı bilgilerini şifreleyerek saklama
  - `get_login_credentials()`: Şifrelenmiş bilgileri çözümleme

### 3. Form Güncellemeleri (`app/forms.py`)
- `ProjectForm`'a yeni alanlar eklendi:
  - `login_enabled`: BooleanField - Otomatik giriş etkinleştirme
  - `login_username`: StringField - Kullanıcı adı
  - `login_password`: PasswordField - Şifre

### 4. Route Güncellemeleri (`app/routes.py`)
- Proje oluşturma route'u güncellendi: Giriş bilgilerini kaydetme
- Proje düzenleme route'u güncellendi: Mevcut bilgileri güncelleme
- Test çalıştırma fonksiyonu güncellendi: Otomatik giriş bilgilerini prompt'a ekleme

### 5. Template Güncellemeleri
- `app/templates/projects/add.html`: Giriş bilgileri form alanları eklendi
- `app/templates/projects/edit.html`: Giriş bilgileri düzenleme alanları eklendi
- JavaScript ile dinamik alan görünümü eklendi

## Kullanım

### Proje Oluşturma/Düzenleme
1. Proje oluştururken veya düzenlerken "Otomatik Giriş Etkin" kutusunu işaretleyin
2. Kullanıcı adı ve şifre bilgilerini girin
3. Şifre güvenli şekilde şifrelenerek saklanır

### Test Sırasında Otomatik Kullanım
- Test çalıştırıldığında, proje için giriş bilgileri varsa:
  - Test prompt'una otomatik giriş talimatları eklenir
  - AI test sırasında "giriş yap", "login ol" komutları karşılaştığında bu bilgileri kullanır

### Güvenlik
- Şifreler Fernet şifreleme ile güvenli şekilde saklanır
- Şifreleme anahtarı Flask SECRET_KEY'den türetilir
- Düzenleme sırasında mevcut şifre korunur (yeni şifre girilmezse)

## Örnek Kullanım Senaryosu

1. **Proje Oluşturma:**
   - Proje adı: "E-ticaret Sitesi Testi"
   - URL: "https://mystore.com"
   - Giriş etkin: ✓
   - Kullanıcı adı: "test@example.com"
   - Şifre: "MySecretPass123"

2. **Test Çalıştırma:**
   - Test prompt'u: "Sepete ürün ekle ve satın al"
   - Sistem otomatik olarak şu talimatları ekler:
     ```
     ÖNEMLI - Otomatik Giriş Bilgileri:
     Bu proje için otomatik giriş etkin. Eğer test sırasında giriş yapman gerekirse:
     - Kullanıcı adı: test@example.com  
     - Şifre: MySecretPass123
     ```

3. **Test Sırasında:**
   - AI giriş sayfasına geldiğinde bu bilgileri otomatik kullanır
   - Manuel giriş yapmaya gerek kalmaz

## Teknik Detaylar

### Şifreleme
```python
from cryptography.fernet import Fernet
# Fernet şifreleme kullanılarak güvenli saklama
```

### Veritabanı Migrasyonu
```bash
python migrate_login_credentials.py
```

Bu komut çalıştırılarak mevcut veritabanı güncellenmiştir.