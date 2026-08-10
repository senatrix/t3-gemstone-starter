from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import atexit
import json
import platform
import shutil
import socket
import subprocess
import threading
import time


# =========================================================
# AYARLAR
# =========================================================

GPIO_LINE = "GPIO4"
PORT = 8000


# =========================================================
# GPIO DURUMU
# =========================================================

gpio_lock = threading.Lock()
gpio_process = None
led_mode = "released"


# =========================================================
# IP ADRESI
# =========================================================

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]

    except Exception:
        return "Bulunamadi"

    finally:
        s.close()


# =========================================================
# CPU
# =========================================================

def read_cpu_times():
    with open("/proc/stat", "r") as f:
        values = [int(x) for x in f.readline().split()[1:]]

    idle = values[3] + values[4]
    total = sum(values)

    return idle, total


def get_cpu_usage():
    idle1, total1 = read_cpu_times()

    time.sleep(0.1)

    idle2, total2 = read_cpu_times()

    idle_delta = idle2 - idle1
    total_delta = total2 - total1

    if total_delta == 0:
        return 0.0

    return 100.0 * (1.0 - idle_delta / total_delta)


# =========================================================
# RAM
# =========================================================

def get_ram():
    meminfo = {}

    with open("/proc/meminfo", "r") as f:
        for line in f:
            key, value = line.split(":", 1)
            meminfo[key] = int(value.strip().split()[0])

    total = meminfo["MemTotal"]
    available = meminfo["MemAvailable"]
    used = total - available

    return {
        "used_mb": used / 1024,
        "total_mb": total / 1024,
        "percent": used / total * 100
    }


# =========================================================
# DISK
# =========================================================

def get_disk():
    total, used, _ = shutil.disk_usage("/")

    gb = 1024 ** 3

    return {
        "used_gb": used / gb,
        "total_gb": total / gb,
        "percent": used / total * 100
    }


# =========================================================
# SOC SICAKLIGI
# =========================================================

def get_temperature():
    path = "/sys/class/thermal/thermal_zone0/temp"

    try:
        with open(path, "r") as f:
            return int(f.read().strip()) / 1000

    except Exception:
        return None


# =========================================================
# UPTIME
# =========================================================

def get_uptime():
    try:
        with open("/proc/uptime", "r") as f:
            seconds = int(float(f.read().split()[0]))

        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60

        return {
            "seconds": seconds,
            "text": f"{days} gun {hours} saat {minutes} dakika"
        }

    except Exception:
        return {
            "seconds": 0,
            "text": "Bulunamadi"
        }


# =========================================================
# WIFI
# =========================================================

def get_wifi():
    try:
        result = subprocess.check_output(
            [
                "nmcli",
                "-g",
                "GENERAL.CONNECTION",
                "device",
                "show",
                "wlan0"
            ],
            text=True,
            timeout=2
        ).strip()

        if result and result != "--":
            return result

        return "Bagli degil"

    except Exception:
        return "Bulunamadi"


# =========================================================
# ISLETIM SISTEMI
# =========================================================

def get_os_name():
    try:
        with open("/etc/os-release", "r") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    return (
                        line
                        .split("=", 1)[1]
                        .strip()
                        .strip('"')
                    )

    except Exception:
        pass

    return platform.system()


# =========================================================
# GPIO PROCESS YONETIMI
# =========================================================

def stop_gpio_process_unlocked():
    global gpio_process

    if gpio_process is not None and gpio_process.poll() is None:
        gpio_process.terminate()

        try:
            gpio_process.wait(timeout=1)

        except subprocess.TimeoutExpired:
            gpio_process.kill()
            gpio_process.wait(timeout=1)

    gpio_process = None


def set_led_mode(mode):
    global gpio_process
    global led_mode

    commands = {
        "on": [
            "gpioset",
            f"{GPIO_LINE}=1"
        ],

        "off": [
            "gpioset",
            f"{GPIO_LINE}=0"
        ],

        "blink": [
            "gpioset",
            "-t500ms",
            f"{GPIO_LINE}=1"
        ]
    }

    if mode not in commands:
        raise ValueError("Gecersiz LED modu")

    with gpio_lock:
        stop_gpio_process_unlocked()

        gpio_process = subprocess.Popen(
            commands[mode],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True
        )

        time.sleep(0.08)

        if gpio_process.poll() is not None:
            error = (
                gpio_process.stderr.read()
                or
                "gpioset baslatilamadi"
            ).strip()

            gpio_process = None
            led_mode = "error"

            raise RuntimeError(error)

        led_mode = mode


def get_led_state():
    global led_mode

    with gpio_lock:
        active = (
            gpio_process is not None
            and gpio_process.poll() is None
        )

        if not active and led_mode in ("on", "off", "blink"):
            led_mode = "released"

        return {
            "mode": led_mode,
            "active": active,
            "gpio": GPIO_LINE
        }


def cleanup_gpio():
    global led_mode

    with gpio_lock:
        stop_gpio_process_unlocked()
        led_mode = "released"


atexit.register(cleanup_gpio)


# =========================================================
# TUM SISTEM VERILERINI TOPLA
# =========================================================

def get_system_data():
    ram = get_ram()
    disk = get_disk()

    return {
        "hostname": socket.gethostname(),
        "ip": get_ip(),

        "cpu": {
            "usage_percent": round(get_cpu_usage(), 1)
        },

        "ram": {
            "used_mb": round(ram["used_mb"], 1),
            "total_mb": round(ram["total_mb"], 1),
            "percent": round(ram["percent"], 1)
        },

        "disk": {
            "used_gb": round(disk["used_gb"], 2),
            "total_gb": round(disk["total_gb"], 2),
            "percent": round(disk["percent"], 1)
        },

        "temperature": get_temperature(),
        "uptime": get_uptime(),
        "wifi": get_wifi(),
        "os": get_os_name(),
        "kernel": platform.release(),
        "led": get_led_state()
    }


# =========================================================
# WEB ARAYUZU
# =========================================================

HTML_PAGE = r"""
<!DOCTYPE html>
<html lang="tr">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>T3 Gemstone O1 System Monitor</title>


<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #0f172a;
    color: white;
}

.container {
    width: 90%;
    max-width: 1100px;
    margin: auto;
    padding: 35px;
}

h1 {
    margin-bottom: 5px;
}

.subtitle,
.card-title,
.chart-title,
.footer {
    color: #94a3b8;
}

.status {
    margin: 15px 0 30px;
    display: inline-block;
    padding: 7px 14px;
    border-radius: 20px;
    background: #14532d;
}

.grid {
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(240px, 1fr));
    gap: 18px;
}

.card,
.control-card,
.chart-card {
    background: #1e293b;
    border-radius: 14px;
    padding: 22px;
}

.value {
    font-size: 26px;
    font-weight: bold;
}

.small-value {
    font-size: 18px;
}

.progress {
    width: 100%;
    height: 10px;
    background: #334155;
    border-radius: 10px;
    margin-top: 15px;
    overflow: hidden;
}

.progress-bar {
    height: 100%;
    background: #38bdf8;
    width: 0%;
    transition: width 0.4s;
}

.control-card,
.chart-card {
    margin-top: 18px;
}

.control-row {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-top: 16px;
}

button {
    border: 0;
    border-radius: 10px;
    padding: 12px 20px;
    font-size: 15px;
    font-weight: bold;
    cursor: pointer;
    background: #334155;
    color: white;
}

button:hover {
    filter: brightness(1.15);
}

button.active {
    outline: 2px solid #38bdf8;
    background: #0c4a6e;
}

#led-message {
    margin-top: 15px;
    color: #cbd5e1;
}

canvas {
    width: 100%;
    height: 220px;
    background: #111827;
    border-radius: 10px;
}

.footer {
    margin-top: 30px;
    font-size: 13px;
}

</style>

</head>


<body>

<div class="container">


<h1>T3 Gemstone O1</h1>

<div class="subtitle">
Canli Embedded Linux Sistem Monitoru + GPIO Kontrol
</div>

<div class="status">
● <span id="connection">API ONLINE</span>
</div>


<div class="grid">


<div class="card">

<div class="card-title">
CPU Kullanimi
</div>

<div class="value" id="cpu">
-- %
</div>

<div class="progress">

<div
    class="progress-bar"
    id="cpu-bar">
</div>

</div>

</div>


<div class="card">

<div class="card-title">
RAM
</div>

<div
    class="value"
    id="ram-percent">
-- %
</div>

<div id="ram-text">
--
</div>

<div class="progress">

<div
    class="progress-bar"
    id="ram-bar">
</div>

</div>

</div>


<div class="card">

<div class="card-title">
Disk
</div>

<div
    class="value"
    id="disk-percent">
-- %
</div>

<div id="disk-text">
--
</div>

<div class="progress">

<div
    class="progress-bar"
    id="disk-bar">
</div>

</div>

</div>


<div class="card">

<div class="card-title">
SoC Sicakligi
</div>

<div
    class="value"
    id="temperature">
--
</div>

</div>


<div class="card">

<div class="card-title">
IP Adresi
</div>

<div
    class="value small-value"
    id="ip">
--
</div>

</div>


<div class="card">

<div class="card-title">
Wi-Fi
</div>

<div
    class="value small-value"
    id="wifi">
--
</div>

</div>


<div class="card">

<div class="card-title">
Hostname
</div>

<div
    class="value small-value"
    id="hostname">
--
</div>

</div>


<div class="card">

<div class="card-title">
Uptime
</div>

<div
    class="value small-value"
    id="uptime">
--
</div>

</div>


<div class="card">

<div class="card-title">
Isletim Sistemi
</div>

<div
    class="value small-value"
    id="os">
--
</div>

</div>


<div class="card">

<div class="card-title">
Linux Kernel
</div>

<div
    class="value small-value"
    id="kernel">
--
</div>

</div>


</div>


<div class="control-card">

<div class="card-title">
GPIO4 - Harici LED Kontrolu
</div>

<div class="value small-value">

Durum:
<span id="led-state">--</span>

</div>


<div class="control-row">

<button
    id="btn-on"
    onclick="setLed('on')">
LED AC
</button>

<button
    id="btn-off"
    onclick="setLed('off')">
LED KAPAT
</button>

<button
    id="btn-blink"
    onclick="setLed('blink')">
YANIP SON
</button>

</div>

<div id="led-message">
GPIO komutu bekleniyor.
</div>

</div>


<div class="chart-card">

<div class="chart-title">
CPU Kullanimi - Son 60 Saniye
</div>

<canvas
    id="cpu-chart"
    width="1000"
    height="220">
</canvas>

</div>


<div class="chart-card">

<div class="chart-title">
SoC Sicakligi - Son 60 Saniye
</div>

<canvas
    id="temp-chart"
    width="1000"
    height="220">
</canvas>

</div>


<div class="footer">
Gemstone REST API |
Veri yenileme: 2 saniye |
GPIO4: libgpiod
</div>


</div>


<script>


const cpuHistory = [];
const tempHistory = [];

const MAX_POINTS = 30;


// =========================================================
// GRAFIK
// =========================================================

function drawChart(
    canvasId,
    values,
    maxValue,
    unit
) {

    const canvas =
        document.getElementById(canvasId);

    const ctx =
        canvas.getContext("2d");

    const width =
        canvas.width;

    const height =
        canvas.height;


    ctx.clearRect(
        0,
        0,
        width,
        height
    );


    ctx.strokeStyle =
        "#334155";

    ctx.lineWidth = 1;


    for (let i = 0; i <= 4; i++) {

        const y =
            (height / 4) * i;

        ctx.beginPath();

        ctx.moveTo(
            0,
            y
        );

        ctx.lineTo(
            width,
            y
        );

        ctx.stroke();
    }


    if (values.length < 2) {
        return;
    }


    ctx.strokeStyle =
        "#38bdf8";

    ctx.lineWidth = 3;

    ctx.beginPath();


    values.forEach(
        (value, index) => {

            const x =
                index /
                (MAX_POINTS - 1) *
                width;

            let normalized =
                value / maxValue;

            normalized =
                Math.max(
                    0,
                    Math.min(
                        1,
                        normalized
                    )
                );

            const y =
                height -
                normalized *
                height;


            if (index === 0) {

                ctx.moveTo(
                    x,
                    y
                );

            } else {

                ctx.lineTo(
                    x,
                    y
                );
            }
        }
    );


    ctx.stroke();


    const last =
        values[
            values.length - 1
        ];


    ctx.fillStyle = "white";
    ctx.font = "20px Arial";


    ctx.fillText(
        last.toFixed(1)
        + " "
        + unit,
        15,
        30
    );
}


// =========================================================
// LED BUTON DURUMU
// =========================================================

function updateLedButtons(mode) {

    [
        "on",
        "off",
        "blink"
    ].forEach(name => {

        document
        .getElementById(
            "btn-" + name
        )
        .classList
        .toggle(
            "active",
            name === mode
        );

    });
}


// =========================================================
// LED REST API
// =========================================================

async function setLed(mode) {

    const message =
        document.getElementById(
            "led-message"
        );


    message.textContent =
        "Komut Gemstone'a gonderiliyor...";


    try {

        const response =
            await fetch(
                "/api/led",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            {
                                mode: mode
                            }
                        )
                }
            );


        const result =
            await response.json();


        if (!response.ok) {

            throw new Error(
                result.error
                ||
                "GPIO hatasi"
            );
        }


        message.textContent =
            "Basarili: GPIO4 modu = "
            + result.mode;


        document
        .getElementById(
            "led-state"
        )
        .textContent =
            result.mode
            .toUpperCase();


        updateLedButtons(
            result.mode
        );

    }

    catch (error) {

        message.textContent =
            "Hata: "
            + error.message;
    }
}


// =========================================================
// SISTEM API
// =========================================================

async function updateDashboard() {

    try {

        const response =
            await fetch(
                "/api/status",
                {
                    cache: "no-store"
                }
            );


        if (!response.ok) {
            throw new Error("HTTP hatasi");
        }


        const data =
            await response.json();


        // CPU

        document
        .getElementById("cpu")
        .textContent =
            data.cpu.usage_percent
            + " %";


        document
        .getElementById("cpu-bar")
        .style.width =
            data.cpu.usage_percent
            + "%";


        cpuHistory.push(
            data.cpu.usage_percent
        );


        if (
            cpuHistory.length >
            MAX_POINTS
        ) {
            cpuHistory.shift();
        }


        drawChart(
            "cpu-chart",
            cpuHistory,
            100,
            "%"
        );


        // RAM

        document
        .getElementById(
            "ram-percent"
        )
        .textContent =
            data.ram.percent
            + " %";


        document
        .getElementById(
            "ram-text"
        )
        .textContent =
            data.ram.used_mb
            + " MB / "
            + data.ram.total_mb
            + " MB";


        document
        .getElementById(
            "ram-bar"
        )
        .style.width =
            data.ram.percent
            + "%";


        // DISK

        document
        .getElementById(
            "disk-percent"
        )
        .textContent =
            data.disk.percent
            + " %";


        document
        .getElementById(
            "disk-text"
        )
        .textContent =
            data.disk.used_gb
            + " GB / "
            + data.disk.total_gb
            + " GB";


        document
        .getElementById(
            "disk-bar"
        )
        .style.width =
            data.disk.percent
            + "%";


        // SICAKLIK

        if (
            data.temperature === null
        ) {

            document
            .getElementById(
                "temperature"
            )
            .textContent =
                "Bulunamadi";

        } else {

            document
            .getElementById(
                "temperature"
            )
            .textContent =
                data.temperature
                .toFixed(1)
                + " °C";


            tempHistory.push(
                data.temperature
            );


            if (
                tempHistory.length >
                MAX_POINTS
            ) {
                tempHistory.shift();
            }


            drawChart(
                "temp-chart",
                tempHistory,
                100,
                "°C"
            );
        }


        document
        .getElementById("ip")
        .textContent =
            data.ip;


        document
        .getElementById("wifi")
        .textContent =
            data.wifi;


        document
        .getElementById("hostname")
        .textContent =
            data.hostname;


        document
        .getElementById("uptime")
        .textContent =
            data.uptime.text;


        document
        .getElementById("os")
        .textContent =
            data.os;


        document
        .getElementById("kernel")
        .textContent =
            data.kernel;


        document
        .getElementById("led-state")
        .textContent =
            data.led.mode
            .toUpperCase();


        updateLedButtons(
            data.led.mode
        );


        document
        .getElementById("connection")
        .textContent =
            "API ONLINE";

    }

    catch (error) {

        document
        .getElementById("connection")
        .textContent =
            "API BAGLANTI HATASI";

        console.error(error);
    }
}


updateDashboard();

setInterval(
    updateDashboard,
    2000
);


</script>

</body>

</html>
"""


# =========================================================
# HTTP SERVER
# =========================================================

class PanelHandler(BaseHTTPRequestHandler):

    def send_json(self, status_code, data):
        payload = json.dumps(data).encode("utf-8")

        self.send_response(status_code)

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )

        self.send_header(
            "Cache-Control",
            "no-store"
        )

        self.end_headers()

        self.wfile.write(payload)


    # =====================================================
    # GET
    # =====================================================

    def do_GET(self):

        if self.path == "/":

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8"
            )

            self.send_header(
                "Cache-Control",
                "no-store"
            )

            self.end_headers()

            self.wfile.write(
                HTML_PAGE.encode("utf-8")
            )


        elif self.path == "/api/status":

            self.send_json(
                200,
                get_system_data()
            )


        elif self.path == "/favicon.ico":

            self.send_response(204)
            self.end_headers()


        else:

            self.send_json(
                404,
                {
                    "error": "Not Found"
                }
            )


    # =====================================================
    # POST
    # =====================================================

    def do_POST(self):

        if self.path != "/api/led":

            self.send_json(
                404,
                {
                    "error": "Not Found"
                }
            )

            return


        try:

            length = int(
                self.headers.get(
                    "Content-Length",
                    "0"
                )
            )

            body = self.rfile.read(length)

            request_data = json.loads(
                body.decode("utf-8")
            )

            mode = request_data.get("mode")

            set_led_mode(mode)


            self.send_json(
                200,
                {
                    "ok": True,
                    "mode": mode,
                    "gpio": GPIO_LINE
                }
            )


        except (
            ValueError,
            json.JSONDecodeError
        ) as error:

            self.send_json(
                400,
                {
                    "ok": False,
                    "error": str(error)
                }
            )


        except Exception as error:

            self.send_json(
                500,
                {
                    "ok": False,
                    "error": str(error)
                }
            )


# =========================================================
# PROGRAM BASLANGICI
# =========================================================

if __name__ == "__main__":

    try:
        set_led_mode("off")

        print(
            f"GPIO baslangic durumu: "
            f"{GPIO_LINE}=OFF"
        )

    except Exception as error:

        print(
            "UYARI: GPIO baslatilamadi:",
            error
        )


    server = ThreadingHTTPServer(
        (
            "0.0.0.0",
            PORT
        ),
        PanelHandler
    )


    print(
        "T3 Gemstone Starter Project v1.0"
    )

    print(
        f"Web : http://0.0.0.0:{PORT}/"
    )

    print(
        f"API : http://0.0.0.0:{PORT}/api/status"
    )

    print(
        "LED : POST /api/led"
    )


    try:
        server.serve_forever()

    except KeyboardInterrupt:
        print(
            "\nSunucu kapatiliyor..."
        )

    finally:
        server.server_close()
        cleanup_gpio()
