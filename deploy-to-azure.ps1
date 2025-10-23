# Azure Container Apps Deployment Script (PowerShell)
# Kullanım: .\deploy-to-azure.ps1 -ResourceGroup "jokeruitest-rg" -AppName "jokeruitest-browser-app"

param(
    [string]$ResourceGroup = "jokeruitest-rg",
    [string]$AppName = "jokeruitest-browser-app", 
    [string]$EnvironmentName = "jokeruitest-env",
    [string]$Location = "West Europe",
    [string]$RegistryName = "myacrjokeruitest1",
    [string]$ImageName = "myacrjokeruitest1.azurecr.io/jokeruitest:v1.0"
)

Write-Host "🚀 Azure Container Apps Deployment başlatılıyor..." -ForegroundColor Green
Write-Host "📋 Resource Group: $ResourceGroup" -ForegroundColor Yellow
Write-Host "📋 App Name: $AppName" -ForegroundColor Yellow
Write-Host "📋 Environment: $EnvironmentName" -ForegroundColor Yellow
Write-Host "📋 Image: $ImageName" -ForegroundColor Yellow

# 1. Resource Group oluştur
Write-Host "📦 Resource Group kontrol ediliyor..." -ForegroundColor Blue
try {
    az group show --name $ResourceGroup | Out-Null
    Write-Host "✅ Resource Group mevcut: $ResourceGroup" -ForegroundColor Green
} catch {
    Write-Host "✨ Resource Group oluşturuluyor: $ResourceGroup" -ForegroundColor Yellow
    az group create --name $ResourceGroup --location $Location
}

# 2. Container Apps Environment oluştur
Write-Host "🌍 Container Apps Environment kontrol ediliyor..." -ForegroundColor Blue
try {
    az containerapp env show --name $EnvironmentName --resource-group $ResourceGroup | Out-Null
    Write-Host "✅ Container Apps Environment mevcut: $EnvironmentName" -ForegroundColor Green
} catch {
    Write-Host "✨ Container Apps Environment oluşturuluyor: $EnvironmentName" -ForegroundColor Yellow
    az containerapp env create --name $EnvironmentName --resource-group $ResourceGroup --location $Location
}

# 3. ACR Login
Write-Host "📦 Azure Container Registry'ye giriş..." -ForegroundColor Blue
az acr login --name $RegistryName

# ACR admin enable
az acr update --name $RegistryName --admin-enabled true

# ACR credentials
$acrUsername = az acr credential show --name $RegistryName --query username --output tsv
$acrPassword = az acr credential show --name $RegistryName --query passwords[0].value --output tsv

# 4. Container App deployment
Write-Host "🔧 Container App deployment..." -ForegroundColor Blue

$envVars = @(
    "FLASK_ENV=production",
    "PORT=5002", 
    "RUNNING_IN_DOCKER=true",
    "AZURE_CONTAINER_APP=true",
    "DOCKER_USER=docker_admin",
    "HEADLESS=false",
    "PYTHONPATH=/app",
    "DISPLAY=:99",
    "LLM_PROVIDER=gemini",
    "LLM_MODEL=gemini-flash-latest",
    "WINDOW_WIDTH=1920",
    "WINDOW_HEIGHT=1080", 
    "IMPLICIT_WAIT=5",
    "EXPLICIT_WAIT=10",
    "MAX_STEPS=50",
    "DATABASE_URL=sqlite:////app/instance/browser_test.db"
)

try {
    az containerapp show --name $AppName --resource-group $ResourceGroup | Out-Null
    Write-Host "🔄 Container App güncelleniyor: $AppName" -ForegroundColor Yellow
    
    az containerapp update `
        --name $AppName `
        --resource-group $ResourceGroup `
        --image $ImageName `
        --set-env-vars $envVars
} catch {
    Write-Host "✨ Container App oluşturuluyor: $AppName" -ForegroundColor Yellow
    
    az containerapp create `
        --name $AppName `
        --resource-group $ResourceGroup `
        --environment $EnvironmentName `
        --image $ImageName `
        --registry-server "$RegistryName.azurecr.io" `
        --registry-username $acrUsername `
        --registry-password $acrPassword `
        --target-port 5002 `
        --ingress external `
        --env-vars $envVars `
        --cpu 2.0 `
        --memory 4Gi `
        --min-replicas 1 `
        --max-replicas 2
}

# 5. Sonuçları göster
Write-Host ""
Write-Host "✅ Deployment tamamlandı!" -ForegroundColor Green

$fqdn = az containerapp show --name $AppName --resource-group $ResourceGroup --query properties.configuration.ingress.fqdn --output tsv
Write-Host "🌐 Container App URL: https://$fqdn" -ForegroundColor Cyan

Write-Host ""
Write-Host "⚠️  MANUEL ADIM GEREKLI:" -ForegroundColor Red
Write-Host "📋 Azure Portal'da aşağıdaki port mapping'i ekleyin:" -ForegroundColor Yellow
Write-Host "   - Container Port: 6080 → Exposed Port: 6080 (External: true)" -ForegroundColor White
Write-Host "   - Container Port: 5900 → Exposed Port: 5900 (External: false)" -ForegroundColor White

Write-Host ""
Write-Host "📋 VNC erişimi için URL (port mapping'den sonra):" -ForegroundColor Yellow
$vncFqdn = $fqdn -replace "--5002", "--6080"
Write-Host "🖥️  VNC URL: https://$vncFqdn/vnc.html" -ForegroundColor Cyan

Write-Host ""
Write-Host "🔍 Logs kontrolü için:" -ForegroundColor Blue
Write-Host "az containerapp logs show --name $AppName --resource-group $ResourceGroup --follow" -ForegroundColor White