#!/usr/bin/env bash
# Build Android APK / AAB using Google Bubblewrap CLI for Trusted Web Activity (TWA)
# Ensures RECORD_AUDIO permission delegation is compiled into the AndroidManifest.xml

set -e

echo "=== RBR Finance Manager - Generador de APK Android (TWA) ==="

# Check bubblewrap installation
if ! command -v bubblewrap &> /dev/null; then
    echo "Instalando @bubblewrap/cli globalmente..."
    npm install -g @bubblewrap/cli
fi

cd "$(dirname "$0")"

if [ ! -f "android.keystore" ]; then
    echo "Generando Android Keystore para firma de la app..."
    keytool -genkey -v -keystore android.keystore -alias rbrfinance -keyalg RSA -keysize 2048 -validity 10000 \
      -storepass rbrfinance2026 -keypass rbrfinance2026 -dname "CN=Albeiro Yaime, OU=RBR, O=RBR Finance, L=Bogota, S=Cundinamarca, C=CO"
fi

echo "Iniciando build de APK con permisos de audio..."
bubblewrap build --manifest twa-manifest.json

echo "=== APK Generado Exitosamente en twa/app-release-signed.apk ==="
