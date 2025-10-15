#!/bin/bash

echo "Starting DNM Container - X11 virtual display..."

# X11 display başlat
Xvfb :0 -screen 0 1920x1080x24 &
XVFB_PID=$!

sleep 3

# Fluxbox window manager başlat
fluxbox &
FLUXBOX_PID=$!

sleep 2

# VNC server başlat
x11vnc -display :0 -nopw -listen localhost -xkb -forever &
VNC_PID=$!

echo "VNC Server started on port 5900"
echo "Connect with VNC viewer to localhost:5900"

# Flask uygulamasını kopyala ve başlat
if [ -d "/app" ]; then
    echo "Starting Flask application..."
    cd /app
    # Port 5000 için environment variable ayarla
    export FLASK_RUN_HOST=0.0.0.0
    export FLASK_RUN_PORT=5005
    python3 run.py &
    FLASK_PID=$!
else
    echo "Flask application directory not found, starting Chrome test instead..."
    # Chrome test başlat
    google-chrome --no-sandbox --disable-dev-shm-usage --disable-gpu --remote-debugging-port=9222 https://www.google.com &
fi

# Cleanup function
cleanup() {
    echo "Cleaning up..."
    kill $FLASK_PID 2>/dev/null || true
    kill $XVFB_PID $FLUXBOX_PID $VNC_PID 2>/dev/null || true
}

trap cleanup EXIT

# Container'ı açık tut
echo "Container is ready. Connect via VNC viewer to localhost:5900"
tail -f /dev/null