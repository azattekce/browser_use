# Python 3.11 slim imajını kullan
FROM python:3.11-slim

# Sistem paketlerini güncelle ve gerekli paketleri yükle
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    x11vnc \
    fluxbox \
    x11-utils \
    procps \
    python3-pip \
    imagemagick \
    && rm -rf /var/lib/apt/lists/*

# NoVNC ve websockify kurulumu
RUN wget -qO- https://github.com/novnc/noVNC/archive/refs/tags/v1.4.0.tar.gz | tar xz -C /opt \
    && mv /opt/noVNC-1.4.0 /opt/novnc \
    && pip install websockify

# Google Chrome'u yükle (modern GPG key yöntemi)
RUN wget -q -O /tmp/google-chrome-key.gpg https://dl.google.com/linux/linux_signing_key.pub \
    && gpg --dearmor /tmp/google-chrome-key.gpg \
    && mv /tmp/google-chrome-key.gpg.gpg /etc/apt/trusted.gpg.d/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/etc/apt/trusted.gpg.d/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/* /tmp/google-chrome-key.gpg

# Chrome ve ChromeDriver test
RUN google-chrome --version

# ChromeDriver'ı yükle
RUN CHROME_DRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE) \
    && wget -N http://chromedriver.storage.googleapis.com/$CHROME_DRIVER_VERSION/chromedriver_linux64.zip -P ~/ \
    && unzip ~/chromedriver_linux64.zip -d ~/ \
    && rm ~/chromedriver_linux64.zip \
    && mv ~/chromedriver /usr/local/bin/chromedriver \
    && chmod +x /usr/local/bin/chromedriver

# Çalışma dizinini ayarla
WORKDIR /app

# Python bağımlılıklarını kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyalarını kopyala
COPY . .

# Veritabanı dosyası için dizin oluştur ve izinleri ayarla
RUN mkdir -p /app/instance && chmod 755 /app/instance
RUN mkdir -p /app/logs && chmod 755 /app/logs
RUN mkdir -p /tmp/chrome_user_data && chmod 777 /tmp/chrome_user_data

# Port'u belirle
EXPOSE 5001 5002 5900 6080 5005

# Çevre değişkenlerini ayarla
ENV FLASK_APP=run.py
ENV FLASK_ENV=production
ENV PYTHONPATH=/app
ENV DISPLAY=:99

# X11 server başlatma scripti oluştur
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "Starting X11 and Flask application..."\n\
\n\
# Eski X11 processlerini temizle\n\
pkill -f "Xvfb :99" || true\n\
pkill -f "fluxbox" || true\n\
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99\n\
\n\
# Instance klasörünü oluştur ve izinleri ayarla\n\
mkdir -p /app/instance\n\
chmod 755 /app/instance\n\
\n\
# X11 server başlat (background)\n\
export DISPLAY=:99\n\
Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &\n\
XVFB_PID=$!\n\
\n\
# X11 serverın hazır olmasını bekle\n\
sleep 3\n\
\n\
# Fluxbox başlat (background)\n\
fluxbox &\n\
FLUXBOX_PID=$!\n\
\n\
# VNC server başlat (background)\n\
echo "Starting VNC server..."\n\
x11vnc -display :99 -nopw -listen localhost -xkb -ncache 10 -ncache_cr -forever &\n\
VNC_PID=$!\n\
sleep 2\n\
\n\
# NoVNC WebSocket proxy başlat\n\
echo "Starting noVNC WebSocket proxy..."\n\
websockify --web /opt/novnc 6080 localhost:5900 &\n\
WEBSOCKIFY_PID=$!\n\
sleep 2\n\
\n\
echo "VNC Server started on port 5900"\n\
echo "noVNC Web interface: http://localhost:6080/vnc.html"\n\
\n\
# X11 bağlantısını test et\n\
timeout 10 sh -c "until xdpyinfo -display :99 >/dev/null 2>&1; do sleep 1; done" || echo "X11 warning: Display may not be ready"\n\
\n\
# Chrome test et\n\
echo "Testing Chrome..."\n\
DISPLAY=:99 google-chrome --headless --no-sandbox --disable-dev-shm-usage --version || echo "Chrome test warning"\n\
\n\
# Chrome user data directory oluştur\n\
mkdir -p /tmp/chrome_user_data\n\
chmod 755 /tmp/chrome_user_data\n\
\n\
# Veritabanı dosyasının izinlerini kontrol et\n\
if [ ! -f /app/instance/browser_test.db ]; then\n\
    touch /app/instance/browser_test.db\n\
    chmod 664 /app/instance/browser_test.db\n\
fi\n\
\n\
echo "VNC Server başlatıldı - Port: 5900"\n\
echo "VNC ile bağlanmak için: localhost:5900"\n\
echo "Browser görünümü için VNC client kullanın"\n\
\n\
echo "Starting Flask application..."\n\
cd /app\n\
python run.py\n\
\n\
# Cleanup on exit\n\
trap "kill $XVFB_PID $FLUXBOX_PID $VNC_PID $WEBSOCKIFY_PID 2>/dev/null || true" EXIT\n\
' > /app/start.sh && chmod +x /app/start.sh

# Duplicate removed - already installed above



# Uygulamayı başlat
CMD ["/app/start.sh"]