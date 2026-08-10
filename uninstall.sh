#!/bin/bash

set -e

SERVICE_NAME="gemstone-panel.service"

echo "========================================"
echo " T3 Gemstone Starter Project Uninstaller"
echo "========================================"

echo
echo "[1/3] Servis durduruluyor..."

sudo systemctl disable --now gemstone-panel 2>/dev/null || true

echo
echo "[2/3] systemd servis dosyasi kaldiriliyor..."

sudo rm -f "/etc/systemd/system/$SERVICE_NAME"

echo
echo "[3/3] systemd yeniden yukleniyor..."

sudo systemctl daemon-reload
sudo systemctl reset-failed

echo
echo "========================================"
echo " Servis kaldirildi."
echo "========================================"

echo
echo "Not:"
echo "Proje kaynak dosyalari silinmedi."
