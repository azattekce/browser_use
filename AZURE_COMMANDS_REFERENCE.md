# Azure Container Apps - Komut Referans Listesi

Bu dokümantasyon, Browser Use projesinin Azure Container Apps deployment sürecinde kullanılan tüm Azure CLI komutlarını içermektedir.

## 📋 Hızlı Komut İndeksi

- [Resource Management](#resource-management)
- [Container Registry](#container-registry)
- [Container Apps](#container-apps)
- [Storage Operations](#storage-operations)
- [Monitoring & Debug](#monitoring--debug)
- [Configuration Management](#configuration-management)

---

## Resource Management

### Resource Group İşlemleri
```bash
# Resource Group oluştur
az group create --name my-rg-jokeruitest1 --location westeurope

# Resource Group listesi
az group list --output table

# Resource Group silme (dikkatli kullan!)
az group delete --name my-rg-jokeruitest1 --yes --no-wait
```

### Subscription ve Location
```bash
# Aktif subscription göster
az account show --query id --output tsv

# Available locations
az account list-locations --query "[].name" --output table
```

---

## Container Registry

### ACR Oluşturma ve Konfigürasyon
```bash
# Container Registry oluştur
az acr create \
  --resource-group my-rg-jokeruitest1 \
  --name myacrjokeruitest1 \
  --sku Basic \
  --location westeurope

# Admin kullanıcısını aktif et
az acr update --name myacrjokeruitest1 --admin-enabled true

# ACR'ye login
az acr login --name myacrjokeruitest1
```

### ACR Credentials
```bash
# Credentials göster
az acr credential show --name myacrjokeruitest1

# Username al
az acr credential show --name myacrjokeruitest1 --query username --output tsv

# Password al
az acr credential show --name myacrjokeruitest1 --query passwords[0].value --output tsv
```

### Image Management
```bash
# ACR'daki repository'leri listele
az acr repository list --name myacrjokeruitest1 --output table

# Spesifik repository'daki tag'leri listele
az acr repository show-tags --name myacrjokeruitest1 --repository jokeruitest --output table

# Image silme
az acr repository delete --name myacrjokeruitest1 --repository jokeruitest --tag v1.0
```

---

## Container Apps

### Environment İşlemleri
```bash
# Container Apps Environment oluştur
az containerapp env create \
  --name myenv-jokeruitest1 \
  --resource-group my-rg-jokeruitest1 \
  --location westeurope

# Environment listesi
az containerapp env list --resource-group my-rg-jokeruitest1 --output table

# Environment detayları
az containerapp env show --name myenv-jokeruitest1 --resource-group my-rg-jokeruitest1
```

### Container App CRUD İşlemleri
```bash
# Container App oluştur
az containerapp create \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --environment myenv-jokeruitest1 \
  --image myacrjokeruitest1.azurecr.io/jokeruitest:v1.0 \
  --registry-server myacrjokeruitest1.azurecr.io \
  --registry-username myacrjokeruitest1 \
  --registry-password "ACR_PASSWORD" \
  --target-port 5002 \
  --ingress external

# Container App listesi
az containerapp list --resource-group my-rg-jokeruitest1 --output table

# Container App detayları
az containerapp show --name jokeruitest-browser-app --resource-group my-rg-jokeruitest1

# Container App silme
az containerapp delete --name jokeruitest-browser-app --resource-group my-rg-jokeruitest1
```

### Image Güncelleme
```bash
# Yeni image version deploy et
az containerapp update \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --image myacrjokeruitest1.azurecr.io/jokeruitest:v1.1

# YAML ile güncelleme
az containerapp update \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --yaml container-app-config.yaml
```

### Environment Variables
```bash
# Environment variables ekle/güncelle
az containerapp update \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --set-env-vars \
    FLASK_ENV=production \
    PORT=5002 \
    RUNNING_IN_DOCKER=true \
    AZURE_CONTAINER_APP=true \
    DATABASE_URL=sqlite:////mnt/database/browser_test.db \
    BROWSER_USE_API_KEY="your-api-key-here"

# Tek environment variable güncelleme
az containerapp update \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --set-env-vars BROWSER_USE_API_KEY="new-api-key"
```

---

## Storage Operations

### Storage Account İşlemleri
```bash
# Storage Account oluştur
az storage account create \
  --name jokeruitest1storage \
  --resource-group my-rg-jokeruitest1 \
  --location westeurope \
  --sku Standard_LRS \
  --kind StorageV2

# Storage Account listesi
az storage account list --resource-group my-rg-jokeruitest1 --output table

# Storage keys göster
az storage account keys list \
  --account-name jokeruitest1storage \
  --resource-group my-rg-jokeruitest1

# İlk key'i al
az storage account keys list \
  --account-name jokeruitest1storage \
  --resource-group my-rg-jokeruitest1 \
  --query "[0].value" \
  --output tsv
```

### File Share İşlemleri
```bash
# File Share oluştur
az storage share create \
  --name database-share \
  --account-name jokeruitest1storage

# File Share listesi
az storage share list --account-name jokeruitest1storage --output table

# File Share detayları
az storage share show \
  --name database-share \
  --account-name jokeruitest1storage
```

### Container Apps Environment Storage
```bash
# Environment'a storage ekle
az containerapp env storage set \
  --name myenv-jokeruitest1 \
  --resource-group my-rg-jokeruitest1 \
  --storage-name database-storage \
  --azure-file-account-name jokeruitest1storage \
  --azure-file-account-key "STORAGE_KEY" \
  --azure-file-share-name database-share \
  --access-mode ReadWrite

# Environment storage listesi
az containerapp env storage list \
  --name myenv-jokeruitest1 \
  --resource-group my-rg-jokeruitest1

# Storage detayları
az containerapp env storage show \
  --name myenv-jokeruitest1 \
  --resource-group my-rg-jokeruitest1 \
  --storage-name database-storage
```

---

## Monitoring & Debug

### Logs İşlemleri
```bash
# Canlı log takibi
az containerapp logs show \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --follow

# Son N satır log
az containerapp logs show \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --tail 20

# Belirli zaman aralığında loglar
az containerapp logs show \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --since 1h
```

### Revision Management
```bash
# Revision listesi
az containerapp revision list \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --output table

# Aktif revision
az containerapp revision show \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --revision REVISION_NAME

# Revision restart
az containerapp revision restart \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --revision REVISION_NAME
```

### Health ve Status Kontrol
```bash
# Container App durumu
az containerapp show \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --query "properties.provisioningState" \
  --output tsv

# Latest revision FQDN
az containerapp show \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --query "properties.latestRevisionFqdn" \
  --output tsv

# Configuration endpoint
az containerapp show \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --query "properties.configuration.ingress.fqdn" \
  --output tsv
```

---

## Configuration Management

### Ingress Konfigürasyonu
```bash
# Ingress detayları
az containerapp ingress show \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1

# Ingress güncelleme (HTTP)
az containerapp ingress update \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --transport http \
  --target-port 5002

# External ingress aktif etme
az containerapp ingress enable \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --type external \
  --target-port 5002 \
  --transport http

# Ingress devre dışı bırakma
az containerapp ingress disable \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1
```

### Template ve Volume Kontrolü
```bash
# Container template detayları
az containerapp show \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --query "properties.template" \
  --output json

# Volume mount kontrolü
az containerapp show \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --query "properties.template.volumes" \
  --output json

# Container volume mounts
az containerapp show \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --query "properties.template.containers[0].volumeMounts" \
  --output json

# Environment variables listesi
az containerapp show \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --query "properties.template.containers[0].env" \
  --output json
```

### Resource ve Scaling
```bash
# CPU/Memory limits güncelleme
az containerapp update \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --cpu 1.0 \
  --memory 2Gi

# Scaling rules
az containerapp update \
  --name jokeruitest-browser-app \
  --resource-group my-rg-jokeruitest1 \
  --min-replicas 1 \
  --max-replicas 3
```

---

## Sık Kullanılan Komut Kombinasyonları

### Hızlı Deployment Check
```bash
# Deployment durumunu kontrol et
APP_NAME="jokeruitest-browser-app"
RG_NAME="my-rg-jokeruitest1"

echo "📊 Container App Status:"
az containerapp show --name $APP_NAME --resource-group $RG_NAME \
  --query "properties.provisioningState" --output tsv

echo "🌐 App URL:"
az containerapp show --name $APP_NAME --resource-group $RG_NAME \
  --query "properties.configuration.ingress.fqdn" --output tsv

echo "🔄 Latest Revision:"
az containerapp show --name $APP_NAME --resource-group $RG_NAME \
  --query "properties.latestRevisionName" --output tsv
```

### Complete Environment Info
```bash
# Tüm environment bilgilerini göster
ENV_NAME="myenv-jokeruitest1"
RG_NAME="my-rg-jokeruitest1"

echo "🏗️ Environment Info:"
az containerapp env show --name $ENV_NAME --resource-group $RG_NAME \
  --query "{name:name, location:location, provisioningState:properties.provisioningState}"

echo "📦 Container Apps in Environment:"
az containerapp list --resource-group $RG_NAME --output table

echo "💾 Environment Storage:"
az containerapp env storage list --name $ENV_NAME --resource-group $RG_NAME --output table
```

### Troubleshooting One-Liner
```bash
# Hızlı troubleshooting bilgileri
APP_NAME="jokeruitest-browser-app"
RG_NAME="my-rg-jokeruitest1"

echo "🔍 Quick Diagnostics for $APP_NAME"
echo "Status: $(az containerapp show --name $APP_NAME --resource-group $RG_NAME --query 'properties.provisioningState' -o tsv)"
echo "URL: https://$(az containerapp show --name $APP_NAME --resource-group $RG_NAME --query 'properties.configuration.ingress.fqdn' -o tsv)"
echo "Revision: $(az containerapp show --name $APP_NAME --resource-group $RG_NAME --query 'properties.latestRevisionName' -o tsv)"
echo "Image: $(az containerapp show --name $APP_NAME --resource-group $RG_NAME --query 'properties.template.containers[0].image' -o tsv)"

echo "📊 Last 5 logs:"
az containerapp logs show --name $APP_NAME --resource-group $RG_NAME --tail 5
```

---

## Environment Variables Reference

Bu deployment'ta kullanılan environment variables:

```bash
FLASK_ENV=production
PORT=5002
RUNNING_IN_DOCKER=true
AZURE_CONTAINER_APP=true
DOCKER_USER=docker_admin
HEADLESS=false
PYTHONPATH=/app
DISPLAY=:99
LLM_PROVIDER=gemini
LLM_MODEL=gemini-flash-latest
WINDOW_WIDTH=1920
WINDOW_HEIGHT=1080
IMPLICIT_WAIT=5
EXPLICIT_WAIT=10
MAX_STEPS=50
DATABASE_URL=sqlite:////mnt/database/browser_test.db
BROWSER_USE_API_KEY=bu_PqcFI9N4MAGyjeuOwHVKotQgN6wOnVs4CLlju85PaM0
```

---

## Azure CLI Extensions

Container Apps için gerekli extension:
```bash
# Container Apps extension yükle (eğer yoksa)
az extension add --name containerapp

# Extension güncellemesi
az extension update --name containerapp

# Yüklü extension'ları listele
az extension list --output table
```

---

## Useful Queries (JMESPath)

Azure CLI'da kullanışlı query'ler:

```bash
# Sadece container app isimlerini al
az containerapp list --resource-group my-rg-jokeruitest1 --query "[].name" -o tsv

# Tüm URL'leri al
az containerapp list --resource-group my-rg-jokeruitest1 \
  --query "[].{name:name, url:properties.configuration.ingress.fqdn}" -o table

# Environment variables'ı formatted göster
az containerapp show --name jokeruitest-browser-app --resource-group my-rg-jokeruitest1 \
  --query "properties.template.containers[0].env[?name=='DATABASE_URL'].value" -o tsv

# Resource kullanımı
az containerapp show --name jokeruitest-browser-app --resource-group my-rg-jokeruitest1 \
  --query "properties.template.containers[0].resources.{cpu:cpu, memory:memory}" -o table
```

Bu komut referansı Azure Container Apps deployment ve management için gereken tüm komutları içermektedir.