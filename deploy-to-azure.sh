#!/bin/bash
# Azure Container Apps Deployment Script
# Kullanım: ./deploy-to-azure.sh <resource-group> <container-app-name> <environment-name>

set -e

# Parametreler
RESOURCE_GROUP=${1:-"jokeruitest-rg"}
APP_NAME=${2:-"jokeruitest-browser-app"}
ENVIRONMENT_NAME=${3:-"jokeruitest-env"}
LOCATION=${4:-"West Europe"}
REGISTRY_NAME="myacrjokeruitest1"
IMAGE_NAME="myacrjokeruitest1.azurecr.io/jokeruitest:v1.0"

echo "🚀 Azure Container Apps Deployment başlatılıyor..."
echo "📋 Resource Group: $RESOURCE_GROUP"
echo "📋 App Name: $APP_NAME"
echo "📋 Environment: $ENVIRONMENT_NAME"
echo "📋 Image: $IMAGE_NAME"

# 1. Resource Group oluştur (eğer yoksa)
echo "📦 Resource Group kontrol ediliyor..."
if ! az group show --name $RESOURCE_GROUP >/dev/null 2>&1; then
    echo "✨ Resource Group oluşturuluyor: $RESOURCE_GROUP"
    az group create --name $RESOURCE_GROUP --location "$LOCATION"
else
    echo "✅ Resource Group mevcut: $RESOURCE_GROUP"
fi

# 2. Container Apps Environment oluştur (eğer yoksa)
echo "🌍 Container Apps Environment kontrol ediliyor..."
if ! az containerapp env show --name $ENVIRONMENT_NAME --resource-group $RESOURCE_GROUP >/dev/null 2>&1; then
    echo "✨ Container Apps Environment oluşturuluyor: $ENVIRONMENT_NAME"
    az containerapp env create \
        --name $ENVIRONMENT_NAME \
        --resource-group $RESOURCE_GROUP \
        --location "$LOCATION"
else
    echo "✅ Container Apps Environment mevcut: $ENVIRONMENT_NAME"
fi

# 3. Azure Container Registry'ye bağlantı (varsa)
echo "📦 Azure Container Registry bağlantısı kontrol ediliyor..."
ACR_SERVER="$REGISTRY_NAME.azurecr.io"
if az acr show --name $REGISTRY_NAME >/dev/null 2>&1; then
    echo "🔑 ACR'ye giriş yapılıyor..."
    az acr login --name $REGISTRY_NAME
    
    # ACR admin enable (gerekirse)
    az acr update --name $REGISTRY_NAME --admin-enabled true
    
    # ACR credentials al
    ACR_USERNAME=$(az acr credential show --name $REGISTRY_NAME --query username --output tsv)
    ACR_PASSWORD=$(az acr credential show --name $REGISTRY_NAME --query passwords[0].value --output tsv)
else
    echo "⚠️  ACR bulunamadı: $REGISTRY_NAME"
    echo "💡 Önce ACR oluşturun: az acr create --name $REGISTRY_NAME --resource-group $RESOURCE_GROUP --sku Standard"
    exit 1
fi

# 4. Container App oluştur veya güncelle
echo "🔧 Container App konfigürasyonu hazırlanıyor..."

# Environment ID'yi al
ENV_ID=$(az containerapp env show --name $ENVIRONMENT_NAME --resource-group $RESOURCE_GROUP --query id --output tsv)

# Secrets oluştur
echo "🔐 Secrets ayarlanıyor..."
az containerapp secret set \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --secrets \
        acr-password=$ACR_PASSWORD \
        secret-key="production-secret-key-change-me-in-production" \
        gemini-api-key="${GEMINI_API_KEY:-placeholder}" \
        openai-api-key="${OPENAI_API_KEY:-placeholder}" \
    --only-show-errors || true

# Container App oluştur veya güncelle
if ! az containerapp show --name $APP_NAME --resource-group $RESOURCE_GROUP >/dev/null 2>&1; then
    echo "✨ Container App oluşturuluyor: $APP_NAME"
    
    az containerapp create \
        --name $APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --environment $ENVIRONMENT_NAME \
        --image $IMAGE_NAME \
        --registry-server $ACR_SERVER \
        --registry-username $ACR_USERNAME \
        --registry-password $ACR_PASSWORD \
        --target-port 5002 \
        --ingress external \
        --secrets \
            acr-password=$ACR_PASSWORD \
            secret-key="production-secret-key-change-me-in-production" \
            gemini-api-key="${GEMINI_API_KEY:-placeholder}" \
            openai-api-key="${OPENAI_API_KEY:-placeholder}" \
        --env-vars \
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
            SECRET_KEY=secretref:secret-key \
            GEMINI_API_KEY=secretref:gemini-api-key \
            OPENAI_API_KEY=secretref:openai-api-key \
            DATABASE_URL="sqlite:////app/instance/browser_test.db" \
        --cpu 2.0 \
        --memory 4Gi \
        --min-replicas 1 \
        --max-replicas 2
else
    echo "🔄 Container App güncelleniyor: $APP_NAME"
    
    az containerapp update \
        --name $APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --image $IMAGE_NAME \
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
            MAX_STEPS=50
fi

# 5. VNC Port mapping (manuel olarak portal'da yapılması gerekebilir)
echo "⚠️  MANUEL ADIM GEREKLI:"
echo "📋 Azure Portal'da aşağıdaki port mapping'i ekleyin:"
echo "   - Container Port: 6080 → Exposed Port: 6080 (External: true)"
echo "   - Container Port: 5900 → Exposed Port: 5900 (External: false)"

# 6. Deployment bilgilerini göster
echo ""
echo "✅ Deployment tamamlandı!"
echo "🌐 Container App URL:"
az containerapp show --name $APP_NAME --resource-group $RESOURCE_GROUP --query properties.configuration.ingress.fqdn --output tsv

echo ""
echo "📋 VNC erişimi için URL (port mapping'den sonra):"
FQDN=$(az containerapp show --name $APP_NAME --resource-group $RESOURCE_GROUP --query properties.configuration.ingress.fqdn --output tsv)
echo "🖥️  VNC URL: https://${FQDN/--5002/--6080}/vnc.html"

echo ""
echo "🔍 Logs kontrolü:"
echo "az containerapp logs show --name $APP_NAME --resource-group $RESOURCE_GROUP --follow"