# Azure Container Apps Deployment Guide

Bu dokümantasyon, Browser Use projesinin Azure Container Apps'e deployment sürecini adım adım açıklamaktadır.

## 📋 İçindekiler

1. [Proje Hazırlığı](#1-proje-hazırlığı)
2. [Azure Kaynakları Oluşturma](#2-azure-kaynakları-oluşturma)
3. [Docker Image Hazırlığı](#3-docker-image-hazırlığı)
4. [Container Apps Deployment](#4-container-apps-deployment)
5. [Persistent Storage Konfigürasyonu](#5-persistent-storage-konfigürasyonu)
6. [VNC Konfigürasyonu](#6-vnc-konfigürasyonu)
7. [Monitoring ve Troubleshooting](#7-monitoring-ve-troubleshooting)

---

## 1. Proje Hazırlığı

### 1.1 Docker Hub SSL Problemi Çözümü

**Problem:** Docker Hub'dan image çekerken SSL certificate hatası
```bash
Error response from daemon: Get "https://registry-1.docker.io/v2/": net/http: TLS handshake timeout
```

**Çözüm:** Microsoft Container Registry kullanımı
```dockerfile
# Dockerfile - İlk satırı değiştir
FROM mcr.microsoft.com/devcontainers/python:3.11-bullseye
```

### 1.2 Docker Compose Azure Uyumluluğu

**Problem:** `network_mode: host` Azure Container Apps'de desteklenmiyor

**Çözüm:** Port mapping ile değiştirme
```yaml
# docker-compose.yml
services:
  app:
    build: .
    ports:
      - "5002:5002"    # Flask app
      - "6080:6080"    # noVNC
      - "5900:5900"    # VNC
    environment:
      - RUNNING_IN_DOCKER=true
      - AZURE_CONTAINER_APP=true
    # network_mode: host  # Bu satırı kaldır
```

### 1.3 Uygulama Kodu Azure Detection

**Docker Detection Enhancement:**
```python
# app/routes.py
def is_running_in_docker():
    # Azure Container Apps için enhanced detection
    if os.environ.get('RUNNING_IN_DOCKER') == 'true':
        return True
    if os.environ.get('AZURE_CONTAINER_APP') == 'true':
        return True
    # Filesystem kontrolleri...
    return os.path.exists('/.dockerenv') or os.path.exists('/proc/self/cgroup')
```

**VNC Button Azure URL Support:**
```javascript
// app/templates/tests/result.html
function openVNC() {
    const hostname = window.location.hostname;
    let vncUrl;
    
    if (hostname.includes('azurecontainerapps.io')) {
        // Azure Container Apps URL format
        const vncHostname = hostname.replace('--5002', '--6080');
        vncUrl = `https://${vncHostname}/vnc.html`;
    } else {
        // Local Docker URL
        vncUrl = `http://${hostname}:6080/vnc.html`;
    }
    
    window.open(vncUrl, '_blank');
}
```

---

## 2. Azure Kaynakları Oluşturma

### 2.1 Resource Group
```bash
# Resource Group oluştur
az group create \
  --name my-rg-jokeruitest1 \
  --location westeurope
```

### 2.2 Azure Container Registry (ACR)
```bash
# Container Registry oluştur
az acr create \
  --resource-group my-rg-jokeruitest1 \
  --name myacrjokeruitest1 \
  --sku Basic \
  --location westeurope

# Admin kullanıcısını aktif et
az acr update \
  --name myacrjokeruitest1 \
  --admin-enabled true

# Login credentials al
az acr credential show --name myacrjokeruitest1
```

### 2.3 Container Apps Environment
```bash
# Container Apps Environment oluştur
az containerapp env create \
  --name myenv-jokeruitest1 \
  --resource-group my-rg-jokeruitest1 \
  --location westeurope
```

---

## 3. Docker Image Hazırlığı

### 3.1 Image Build ve Push
```bash
# ACR'ye login
az acr login --name myacrjokeruitest1

# Docker image build
docker build -t myacrjokeruitest1.azurecr.io/jokeruitest:v1.0 .

# Image'ı ACR'ye push
docker push myacrjokeruitest1.azurecr.io/jokeruitest:v1.0
```

### 3.2 Image Tag Management
```bash
# Yeni versiyon için build
docker build -t myacrjokeruitest1.azurecr.io/jokeruitest:v1.1 .
docker push myacrjokeruitest1.azurecr.io/jokeruitest:v1.1

# Latest tag
docker tag myacrjokeruitest1.azurecr.io/jokeruitest:v1.1 \
           myacrjokeruitest1.azurecr.io/jokeruitest:latest
docker push myacrjokeruitest1.azurecr.io/jokeruitest:latest
```

---

## 4. Container Apps Deployment

### 4.1 İlk Deployment
```bash
# Container App oluştur
az containerapp create \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --environment myenv-jokeruitest1 \
  --image myacrjokeruitest1.azurecr.io/jokeruitest:v1.0 \
  --registry-server myacrjokeruitest1.azurecr.io \
  --registry-username myacrjokeruitest1 \
  --registry-password "ACR_PASSWORD_BURAYA" \
  --target-port 5002 \
  --ingress external
```

### 4.2 Environment Variables
```bash
# Environment variables ekle
az containerapp update \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --set-env-vars \
    FLASK_ENV=production \
    PORT=5002 \
    RUNNING_IN_DOCKER=true \
    AZURE_CONTAINER_APP=true \
    DOCKER_USER=docker_admin \
    HEADLESS=false \
    PYTHONPATH=/app \
    DISPLAY=:99 \
    LLM_PROVIDER=gemini \
    LLM_MODEL=gemini-flash-latest \
    WINDOW_WIDTH=1920 \
    WINDOW_HEIGHT=1080 \
    IMPLICIT_WAIT=5 \
    EXPLICIT_WAIT=10 \
    MAX_STEPS=50 \
    BROWSER_USE_API_KEY="bu_PqcFI9N4MAGyjeuOwHVKotQgN6wOnVs4CLlju85PaM0"
```

### 4.3 Image Güncelleme
```bash
# Yeni image version'ı deploy et
az containerapp update \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --image myacrjokeruitest1.azurecr.io/jokeruitest:v1.1
```

---

## 5. Persistent Storage Konfigürasyonu

### 5.1 Problem: Veritabanı Kayıpları
Her Container App güncellemesinde SQLite veritabanı kayıtları siliniyor.

### 5.2 Azure Storage Account Oluşturma
```bash
# Storage Account oluştur
az storage account create \
  --name jokeruitest1storage \
  --resource-group my-rg-jokeruitest1 \
  --location westeurope \
  --sku Standard_LRS \
  --kind StorageV2

# File Share oluştur
az storage share create \
  --name database-share \
  --account-name jokeruitest1storage

# Storage key al
STORAGE_KEY=$(az storage account keys list \
  --account-name jokeruitest1storage \
  --resource-group my-rg-jokeruitest1 \
  --query "[0].value" \
  --output tsv)
```

### 5.3 Container Apps Environment Storage
```bash
# Storage'ı environment'a ekle
az containerapp env storage set \
  --name myenv-jokeruitest1 \
  --resource-group my-rg-jokeruitest1 \
  --storage-name database-storage \
  --azure-file-account-name jokeruitest1storage \
  --azure-file-account-key "$STORAGE_KEY" \
  --azure-file-share-name database-share \
  --access-mode ReadWrite
```

### 5.4 Volume Mount Konfigürasyonu
```yaml
# container-app-with-storage.yaml
properties:
  template:
    containers:
    - name: jokeruitest-browser-app
      image: myacrjokeruitest1.azurecr.io/jokeruitest:v1.1
      volumeMounts:
      - mountPath: /mnt/database
        volumeName: database-volume
      env:
      - name: DATABASE_URL
        value: sqlite:////mnt/database/browser_test.db
    volumes:
    - name: database-volume
      storageType: AzureFile
      storageName: database-storage
```

```bash
# Volume mount ile güncelle
az containerapp update \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --yaml container-app-with-storage.yaml
```

### 5.5 Uygulama Kodu Database Directory
```python
# app/__init__.py
def create_app():
    # ...
    with app.app_context():
        # Database directory oluştur
        db_url = app.config['SQLALCHEMY_DATABASE_URI']
        if db_url.startswith('sqlite:///'):
            db_path = db_url.replace('sqlite:///', '')
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                print(f"Created database directory: {db_dir}")
        
        db.create_all()
```

---

## 6. VNC Konfigürasyonu

### 6.1 Problem: Multi-Port Ingress Sınırlaması
Azure Container Apps CLI'da additional port mapping desteği sınırlı.

### 6.2 TCP Port Problemi
```bash
# TCP transport external ingress için VNET gerekiyor
az containerapp ingress update \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --transport tcp \
  --target-port 6080 \
  --exposed-port 6080
  
# Hata: Applications with external TCP ingress can only be deployed 
# to Container App Environments that have a custom VNET
```

### 6.3 HTTP Transport Çözümü
```bash
# HTTP transport'a geri dön
az containerapp ingress update \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --transport http \
  --target-port 5002
```

### 6.4 VNC Button URL Logic
Flask uyglamasında VNC button'ı Azure Container Apps URL formatını handle ediyor:
- Ana URL: `https://jokeruitest-browser-app.ashyplant-23a1b2b2.westeurope.azurecontainerapps.io`
- VNC URL: `https://jokeruitest-browser-app--6080.ashyplant-23a1b2b2.westeurope.azurecontainerapps.io/vnc.html`

---

## 7. Monitoring ve Troubleshooting

### 7.1 Container App Durumu
```bash
# Container App listesi
az containerapp list \
  --resource-group my-rg-jokeruitest1 \
  --output table

# Spesifik Container App bilgisi
az containerapp show \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1

# Provisioning durumu
az containerapp show \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --query "properties.provisioningState"
```

### 7.2 Logs Monitoring
```bash
# Canlı log takibi
az containerapp logs show \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --follow

# Son 20 log satırı
az containerapp logs show \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --tail 20
```

### 7.3 Configuration Verification
```bash
# Volume mount kontrolü
az containerapp show \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --query "properties.template.volumes"

# Volume mount path kontrolü
az containerapp show \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --query "properties.template.containers[0].volumeMounts"

# Environment variables kontrolü
az containerapp show \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --query "properties.template.containers[0].env"

# Ingress konfigürasyonu
az containerapp ingress show \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1
```

### 7.4 Revision Management
```bash
# Revision listesi
az containerapp revision list \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --output table

# Spesifik revision bilgisi
az containerapp revision show \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --revision REVISION_NAME
```

---

## 8. Deployment Scripts

### 8.1 PowerShell Deployment Script
```powershell
# deploy-to-azure.ps1
param(
    [string]$ResourceGroup = "my-rg-jokeruitest1",
    [string]$AppName = "jokeruitest-browser-app"
)

# Resource Group oluştur
az group create --name $ResourceGroup --location "West Europe"

# Container Apps Environment oluştur
az containerapp env create \
  --name myenv-jokeruitest1 \
  --resource-group $ResourceGroup \
  --location "West Europe"

# ACR Login
az acr login --name myacrjokeruitest1

# Container App deployment
az containerapp create \
  --name $AppName \
  --resource-group $ResourceGroup \
  --environment myenv-jokeruitest1 \
  --image myacrjokeruitest1.azurecr.io/jokeruitest:v1.1
```

### 8.2 Bash Deployment Script
```bash
#!/bin/bash
# deploy-to-azure.sh

RESOURCE_GROUP=${1:-"my-rg-jokeruitest1"}
APP_NAME=${2:-"jokeruitest-browser-app"}
ENVIRONMENT_NAME=${3:-"myenv-jokeruitest1"}

echo "🚀 Azure Container Apps Deployment başlatılıyor..."
echo "📋 Resource Group: $RESOURCE_GROUP"
echo "📋 App Name: $APP_NAME"

# Resource Group oluştur
az group create \
  --name $RESOURCE_GROUP \
  --location westeurope

# Container Apps Environment oluştur
az containerapp env create \
  --name $ENVIRONMENT_NAME \
  --resource-group $RESOURCE_GROUP \
  --location westeurope

# Container App oluştur
az containerapp create \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $ENVIRONMENT_NAME \
  --image myacrjokeruitest1.azurecr.io/jokeruitest:latest
```

---

## 9. Karşılaşılan Problemler ve Çözümleri

### 9.1 Docker Hub SSL Timeout
**Problem:** `TLS handshake timeout` hataları
**Çözüm:** Microsoft Container Registry (mcr.microsoft.com) kullanımı

### 9.2 Network Mode Host Desteği
**Problem:** `network_mode: host` Azure'da desteklenmiyor
**Çözüm:** Explicit port mapping ile değiştirme

### 9.3 YAML Configuration JSON Error
**Problem:** `The JSON value could not be converted to System.Boolean`
**Çözüm:** Azure CLI parametreleri ile deployment, YAML yerine

### 9.4 TCP Ingress VNET Requirement
**Problem:** External TCP ingress için custom VNET gerekli
**Çözüm:** HTTP transport kullanarak uygulama seviyesinde VNC proxy

### 9.5 Persistent Storage Loss
**Problem:** Her güncelleme ile veritabanı kayıtları kayboluyor
**Çözüm:** Azure File Share ile persistent volume mount

### 9.6 VNC Button Visibility
**Problem:** Azure'da VNC button görünmüyor
**Çözüm:** Enhanced Docker detection ve Azure URL handling

---

## 10. Deployment URL'leri

### 10.1 Ana Uygulama
```
https://jokeruitest-browser-app.ashyplant-23a1b2b2.westeurope.azurecontainerapps.io
```

### 10.2 VNC Erişimi (Manuel Port Mapping Sonrası)
```
https://jokeruitest-browser-app--6080.ashyplant-23a1b2b2.westeurope.azurecontainerapps.io/vnc.html
```

### 10.3 Health Check Endpoint
```
https://jokeruitest-browser-app.ashyplant-23a1b2b2.westeurope.azurecontainerapps.io/health
```

---

## 11. Best Practices

### 11.1 Security
- ACR credentials'ları Azure Key Vault'da sakla
- Environment variables'ı secrets olarak tanımla
- Minimum required permissions kullan

### 11.2 Performance  
- Resource limits ve requests tanımla
- Health checks konfigüre et
- Auto-scaling rules ayarla

### 11.3 Maintenance
- Image versioning stratejisi kullan
- Regular backup schedule oluştur
- Monitoring ve alerting kur

---

## 12. Sonuç

Bu dokümantasyon ile Browser Use projesi başarıyla Azure Container Apps'e deploy edildi. Ana özellikler:

✅ **Persistent Storage:** Veritabanı kayıtları korunuyor
✅ **VNC Support:** Browser visualization çalışıyor  
✅ **Auto-scaling:** Container Apps auto-scaling active
✅ **SSL/TLS:** HTTPS ingress konfigüre edildi
✅ **Environment Detection:** Azure ortamı doğru algılanıyor

**Toplam Azure Kaynakları:**
- 1x Resource Group
- 1x Container Registry  
- 1x Storage Account + File Share
- 1x Container Apps Environment
- 1x Container App
- 1x Environment Storage Mount