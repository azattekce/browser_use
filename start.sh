#!/bin/bash

# Database dizinini oluştur ve izinlerini ayarla
echo "Setting up database directory..."
mkdir -p /app/instance
chmod 755 /app/instance

# Environment değişkenlerini ayarla
export DATABASE_URL="sqlite:////app/instance/browser_test.db"
export FLASK_ENV="production"
export SECRET_KEY="${SECRET_KEY:-production-secret-key}"

echo "Database will be created at: $DATABASE_URL"

# X server'ı başlat (eski process varsa temizle)
pkill -f Xvfb
rm -f /tmp/.X99-lock

echo "Starting X11 server on display :99..."
Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
XVFB_PID=$!

# X server'ın başlamasını bekle
sleep 3

# X server'ın çalıştığını kontrol et
if xdpyinfo -display :99 >/dev/null 2>&1; then
    echo "X11 server successfully started"
else
    echo "Failed to start X11 server"
    exit 1
fi

export DISPLAY=:99

echo "Starting Flask application..."
cd /app
python run.py