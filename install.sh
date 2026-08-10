#!/bin/bash

set -e

PROJECT_DIR="/home/gemstone/gemstone-projects/gemstone-starter"
SERVICE_NAME="gemstone-panel.service"

echo "========================================"
echo " T3 Gemstone Starter Project v1.0"
echo "========================================"

echo
echo "[1/5] Python kontrol ediliyor..."
python3 --version

echo
echo "[2/5] GPIO araci kontrol ediliyor..."
command -v gpioset

echo
echo "[3/5] Uygulama kontrol ediliyor..."
python3 -m py_compile "$PROJECT_DIR/app.py"

echo
echo "[4/5] systemd servisi kuruluyor..."

sudo systemctl stop gemstone-panel 2>/dev/null || true

sudo cp \
    "$PROJECT_DIR/$SERVICE_NAME" \
    "/etc/systemd/system/$SERVICE_NAME"

sudo systemctl daemon-reload

echo
echo "[5/5] Servis baslatiliyor..."

sudo systemctl enable --now gemstone-panel

echo
echo "========================================"
echo " Kurulum tamamlandi."
echo "========================================"

echo
echo "Servis:"
systemctl status gemstone-panel --no-pager

echo
echo "IP adresleri:"
hostname -I

echo
echo "Web paneli:"
echo "http://GEMSTONE_IP:8000"
