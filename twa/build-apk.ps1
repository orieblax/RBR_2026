# Build Android APK / AAB using Google Bubblewrap CLI on Windows
Write-Host "=== RBR Finance Manager - Generador de APK Android (TWA) ===" -ForegroundColor Cyan

$bubblewrapCmd = Get-Command bubblewrap -ErrorAction SilentlyContinue
if (-not $bubblewrapCmd) {
    Write-Host "Instalando @bubblewrap/cli..." -ForegroundColor Yellow
    npm install -g @bubblewrap/cli
}

Set-Location $PSScriptRoot

if (-not (Test-Path "android.keystore")) {
    Write-Host "Generando Android Keystore..." -ForegroundColor Yellow
    keytool -genkey -v -keystore android.keystore -alias rbrfinance -keyalg RSA -keysize 2048 -validity 10000 `
      -storepass rbrfinance2026 -keypass rbrfinance2026 -dname "CN=Albeiro Yaime, OU=RBR, O=RBR Finance, L=Bogota, S=Cundinamarca, C=CO"
}

Write-Host "Compilando TWA con permisos de RECORD_AUDIO..." -ForegroundColor Green
bubblewrap build --manifest twa-manifest.json
Write-Host "=== Proceso Finalizado ===" -ForegroundColor Cyan
