# T3 Gemstone O1 Starter Project v1.0

T3 Gemstone O1 üzerinde Embedded Linux geliştirme mantığını öğrenmek amacıyla hazırlanmış başlangıç projesidir.

Proje; sistem bilgilerinin web üzerinden izlenmesini, REST API kullanımını, Linux GPIO kontrolünü ve uygulamanın `systemd` servisi olarak otomatik başlatılmasını içerir.

## Özellikler

- Wi-Fi üzerinden web arayüzü
- Python tabanlı HTTP sunucusu
- REST API
- CPU kullanım takibi
- RAM kullanım takibi
- Disk kullanım takibi
- SoC sıcaklık takibi
- Sistem uptime bilgisi
- İşletim sistemi bilgisi
- Linux kernel bilgisi
- Wi-Fi bağlantı bilgisi
- Canlı CPU kullanım grafiği
- Canlı SoC sıcaklık grafiği
- GPIO4 üzerinden harici LED kontrolü
- LED ON / OFF / Blink kontrolü
- `systemd` ile otomatik başlangıç
- Kurulum ve kaldırma scriptleri

## Kullanılan Teknolojiler

- T3 Gemstone O1
- Embedded Linux
- Python 3
- HTML
- CSS
- JavaScript
- HTTP
- REST API
- JSON
- libgpiod
- systemd
- NetworkManager

## Proje Yapısı

```text
gemstone-starter/
├── app.py
├── gemstone-panel.service
├── install.sh
├── uninstall.sh
└── README.md
```

## Sistem Mimarisi

```text
                 Wi-Fi / HTTP
                      |
                      v
+------------------------------------------+
|              Web Browser                 |
|        HTML + CSS + JavaScript           |
+--------------------+---------------------+
                     |
                     | REST API / JSON
                     v
+------------------------------------------+
|          T3 Gemstone O1                  |
|                                          |
|              app.py                      |
|          Python HTTP Server              |
|                                          |
|  +----------------+  +----------------+  |
|  | System Monitor |  | GPIO Control   |  |
|  +-------+--------+  +-------+--------+  |
|          |                   |            |
|          v                   v            |
|      /proc /sys          libgpiod         |
|                              |            |
+------------------------------+------------+
                               |
                               v
                             GPIO4
                               |
                               v
                              LED
```

## Donanım Bağlantısı

Harici LED `GPIO4` üzerinden kontrol edilmektedir.

```text
GPIO4
  |
  |
330 ohm
  |
  |
LED Anot
LED Katot
  |
  |
 GND
```

LED doğrudan GPIO pinine dirençsiz bağlanmamalıdır.

## Manuel Çalıştırma

Proje klasörüne girin:

```bash
cd ~/gemstone-projects/gemstone-starter
```

Uygulamayı çalıştırın:

```bash
python3 app.py
```

Varsayılan HTTP portu:

```text
8000
```

## Kurulum

Kurulum scriptine çalıştırma izni verin:

```bash
chmod +x install.sh
```

Kurulumu başlatın:

```bash
./install.sh
```

Kurulum scripti:

1. Python 3 kurulumunu kontrol eder.
2. `gpioset` aracını kontrol eder.
3. `app.py` dosyasının Python sözdizimini kontrol eder.
4. `systemd` servis dosyasını sisteme kurar.
5. Servisi etkinleştirir ve başlatır.

## IP Adresini Öğrenme

Gemstone IP adreslerini görmek için:

```bash
hostname -I
```

Wi-Fi arayüzünün aldığı IP adresi kullanılarak web paneline erişilebilir.

Örnek:

```text
http://192.168.2.154:8000
```

IP adresi DHCP nedeniyle değişebilir.

## Web Arayüzü

Web panelinde aşağıdaki bilgiler görüntülenir:

- CPU kullanımı
- RAM kullanımı
- Disk kullanımı
- SoC sıcaklığı
- IP adresi
- Wi-Fi bağlantısı
- Hostname
- Sistem uptime
- İşletim sistemi
- Linux kernel sürümü
- CPU kullanım grafiği
- SoC sıcaklık grafiği
- GPIO4 LED kontrolü

## REST API

### Sistem Durumu

Endpoint:

```text
GET /api/status
```

Örnek cevap:

```json
{
    "hostname": "gemstone",
    "ip": "192.168.2.154",
    "cpu": {
        "usage_percent": 5.3
    },
    "ram": {
        "used_mb": 170.2,
        "total_mb": 3789.0,
        "percent": 4.5
    },
    "temperature": 49.2
}
```

### LED Kontrolü

Endpoint:

```text
POST /api/led
```

LED açmak için:

```json
{
    "mode": "on"
}
```

LED kapatmak için:

```json
{
    "mode": "off"
}
```

LED'i yanıp söndürmek için:

```json
{
    "mode": "blink"
}
```

## GPIO Kontrolü

Proje Linux GPIO kontrolü için `libgpiod` araçlarını kullanır.

LED açma mantığı:

```bash
gpioset GPIO4=1
```

LED kapatma mantığı:

```bash
gpioset GPIO4=0
```

Blink:

```bash
gpioset -t500ms GPIO4=1
```

Python uygulaması bu işlemleri arka planda yönetir.

## systemd Servisi

Servis adı:

```text
gemstone-panel
```

Servis durumunu kontrol etmek için:

```bash
systemctl status gemstone-panel --no-pager
```

Servisin çalışıp çalışmadığını kısa şekilde kontrol etmek için:

```bash
systemctl is-active gemstone-panel
```

Beklenen çıktı:

```text
active
```

Otomatik başlangıcın etkin olup olmadığını kontrol etmek için:

```bash
systemctl is-enabled gemstone-panel
```

Beklenen çıktı:

```text
enabled
```

Servisi yeniden başlatmak için:

```bash
sudo systemctl restart gemstone-panel
```

Servisi durdurmak için:

```bash
sudo systemctl stop gemstone-panel
```

Servis loglarını canlı izlemek için:

```bash
journalctl -u gemstone-panel -f
```

## Otomatik Başlangıç

`gemstone-panel.service` sayesinde uygulama Gemstone açıldığında otomatik olarak çalışır.

Akış:

```text
Gemstone Boot
      |
      v
Linux
      |
      v
systemd
      |
      v
gemstone-panel.service
      |
      v
app.py
      |
      v
Web Dashboard + REST API + GPIO
```

Bu nedenle her yeniden başlatmadan sonra elle:

```bash
python3 app.py
```

komutunun çalıştırılması gerekmez.

## Kaldırma

Kaldırma scriptine çalıştırma izni verin:

```bash
chmod +x uninstall.sh
```

Ardından:

```bash
./uninstall.sh
```

Bu işlem `systemd` servisini kaldırır ancak proje kaynak dosyalarını silmez.

## Öğrenilen Temel Konular

Bu proje kapsamında aşağıdaki konular uygulamalı olarak kullanılmıştır:

- SSH bağlantısı
- Wi-Fi ağ yapılandırması
- Linux ağ arayüzleri
- Embedded Linux
- Python
- `/proc` sanal dosya sistemi
- `/sys` arayüzü
- HTTP
- REST API
- JSON
- HTML
- CSS
- JavaScript
- Linux GPIO
- libgpiod
- systemd servisleri
- Otomatik uygulama başlatma

## Amaç

Bu proje, T3 Gemstone O1 üzerinde daha gelişmiş donanım, kamera, yapay zeka ve Edge AI projelerine geçmeden önce temel geliştirme ortamını ve Embedded Linux çalışma mantığını öğrenmek için hazırlanmıştır.
