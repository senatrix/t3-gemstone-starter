# =========================================================

def get_os_name():

    try:

        with open(
            "/etc/os-release",
            "r"
        ) as f:

            for line in f:

                if line.startswith(
                    "PRETTY_NAME="
                ):

                    return (
                        line
                        .split(
                            "=",
                            1
                        )[1]
                        .strip()
                        .strip('"')
                    )

    except Exception:
        pass

    return platform.system()


# =========================================================
# GPIO PROCESS DURDUR
# =========================================================

def _stop_gpio_process_unlocked():

    global _gpio_process

    if (
        _gpio_process is not None
        and
        _gpio_process.poll()
        is None
    ):

        _gpio_process.terminate()

        try:

            _gpio_process.wait(
                timeout=1
            )

        except subprocess.TimeoutExpired:

            _gpio_process.kill()

            _gpio_process.wait(
                timeout=1
            )

    _gpio_process = None


# =========================================================
# LED MODUNU DEGISTIR
# =========================================================

def set_led_mode(mode):

    global _gpio_process
    global _led_mode

    commands = {

        "on":
            [
                "gpioset",
                f"{GPIO_LINE}=1"
            ],

        "off":
            [
                "gpioset",
                f"{GPIO_LINE}=0"
            ],

        "blink":
            [
                "gpioset",
                "-t500ms",
                f"{GPIO_LINE}=1"
            ]
    }

    if mode not in commands:

        raise ValueError(
            "Gecersiz LED modu"
        )

    with _gpio_lock:

        # Önce varsa eski gpioset
        # prosesini kapat.
        _stop_gpio_process_unlocked()

        # Yeni gpioset prosesini başlat.
        _gpio_process = (
            subprocess.Popen(
                commands[mode],

                stdout=
                    subprocess.DEVNULL,

                stderr=
                    subprocess.PIPE,

                text=True
            )
        )

        # gpioset hemen hata verdi mi
        # kontrol etmek için çok kısa bekle.
        time.sleep(0.08)

        if (
            _gpio_process.poll()
            is not None
        ):

            error = (
                _gpio_process
                .stderr
                .read()
                or
                "gpioset baslatilamadi"
            ).strip()

            _gpio_process = None

            _led_mode = "error"

            raise RuntimeError(
                error
            )

        _led_mode = mode


# =========================================================
# LED DURUMU
# =========================================================

def get_led_state():

    global _led_mode

    with _gpio_lock:

        alive = (

            _gpio_process
            is not None

            and

            _gpio_process.poll()
            is None
        )

        if (
            not alive
            and
            _led_mode in
            (
                "on",
                "off",
                "blink"
            )
        ):

            _led_mode = "released"

        return {

            "mode":
                _led_mode,

            "active":
                alive,

            "gpio":
                GPIO_LINE
        }


# =========================================================
# PROGRAM KAPANIRKEN GPIO'YU SERBEST BIRAK
# =========================================================

def cleanup_gpio():

    global _led_mode

    with _gpio_lock:

        _stop_gpio_process_unlocked()

        _led_mode = "released"


atexit.register(
    cleanup_gpio
)


# =========================================================
# TUM SISTEM VERILERI
# =========================================================

def get_system_data():

    ram = get_ram()

    disk = get_disk()

    return {

        "hostname":
            socket.gethostname(),

        "ip":
            get_ip(),

        "cpu": {

            "usage_percent":
                round(
                    get_cpu_usage(),
                    1
                )
        },

        "ram": {

            "used_mb":
                round(
                    ram["used_mb"],
                    1
                ),

            "total_mb":
                round(
                    ram["total_mb"],
                    1
                ),

            "percent":
                round(
                    ram["percent"],
                    1
                )
        },

        "disk": {

            "used_gb":
                round(
                    disk["used_gb"],
                    2
                ),

            "total_gb":
                round(
                    disk["total_gb"],
                    2
                ),

            "percent":
                round(
                    disk["percent"],
                    1
                )
        },

        "temperature":
            get_temperature(),

        "uptime":
            get_uptime(),

        "wifi":
            get_wifi(),

        "os":
            get_os_name(),

        "kernel":
            platform.release(),

        "led":
            get_led_state()
    }


# =========================================================
# WEB ARAYUZU
# =========================================================

HTML_PAGE = r'''
<!DOCTYPE html>

<html lang="tr">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>
Gemstone System Monitor
</title>


<style>

* {
    box-sizing: border-box;
}


body {

    margin: 0;

    font-family:
        Arial,
        sans-serif;

    background:
        #0f172a;

    color:
        white;
}


.container {

    width:
        90%;

    max-width:
        1100px;

    margin:
        auto;

    padding:
        35px;
}


h1 {

    margin-bottom:
        5px;
}


.subtitle,
.card-title,
.chart-title,
.footer {

    color:
        #94a3b8;
}


.status {

    margin:
        15px 0 30px;

    display:
        inline-block;

    padding:
        7px 14px;

    border-radius:
        20px;

    background:
        #14532d;
}


.grid {

    display:
        grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(
                240px,
                1fr
            )
        );

    gap:
        18px;
}


.card,
.chart-card,
.control-card {

    background:
        #1e293b;

    border-radius:
        14px;

    padding:
        22px;
}


.value {

    font-size:
        26px;

    font-weight:
        bold;
}


.small-value {

    font-size:
        18px;
}


.progress {

    width:
        100%;

    height:
        10px;

    background:
        #334155;

    border-radius:
        10px;

    margin-top:
        15px;

    overflow:
        hidden;
}


.progress-bar {

    height:
        100%;

    background:
        #38bdf8;

    width:
        0%;

    transition:
        width 0.4s;
}


/* =====================================================
   GPIO KONTROL PANELI
   ===================================================== */

.control-card {

    margin-top:
        18px;
}


.control-row {

    display:
        flex;

    flex-wrap:
        wrap;

    gap:
        12px;

    margin-top:
        16px;
}


button {

    border:
        0;

    border-radius:
        10px;

    padding:
        12px 20px;

    font-size:
        15px;

    font-weight:
        bold;

    cursor:
        pointer;

    background:
        #334155;

    color:
        white;
}


button:hover {

    filter:
        brightness(1.15);
}


button.active {

    outline:
        2px solid #38bdf8;

    background:
        #0c4a6e;
}


#led-message {

    margin-top:
        15px;

    color:
        #cbd5e1;
}


/* =====================================================
   GRAFIK
   ===================================================== */

.chart-card {

    margin-top:
        18px;
}


canvas {

    width:
        100%;

    height:
        220px;

    background:
        #111827;

    border-radius:
        10px;
}


.footer {

    margin-top:
        30px;

    font-size:
        13px;
}

</style>

</head>


<body>


<div class="container">


<h1>
T3 Gemstone O1
</h1>


<div class="subtitle">

Canli Embedded Linux
Sistem Monitoru + GPIO Kontrol

</div>


<div class="status">

●

<span id="connection">
API ONLINE
</span>

</div>



<!-- =====================================================
     SISTEM BILGILERI
     ===================================================== -->

<div class="grid">


<div class="card">

<div class="card-title">
CPU Kullanimi
</div>

<div
    class="value"
    id="cpu">

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



<!-- =====================================================
     GPIO LED KONTROLU
     ===================================================== -->

<div class="control-card">


<div class="card-title">

GPIO4 - Harici LED Kontrolu

</div>


<div class="value small-value">

Durum:

<span id="led-state">
--
</span>

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



<!-- =====================================================
     CPU GRAFIGI
     ===================================================== -->

<div class="chart-card">

<div class="chart-title">

CPU Kullanimi -
Son 60 Saniye

</div>

<canvas
    id="cpu-chart"
    width="1000"
    height="220">
</canvas>

</div>



<!-- =====================================================
     SICAKLIK GRAFIGI
     ===================================================== -->

<div class="chart-card">

<div class="chart-title">

SoC Sicakligi -
Son 60 Saniye

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


// =====================================================
// GRAFIK HAFIZASI
// =====================================================

const cpuHistory = [];

const tempHistory = [];

const MAX_POINTS = 30;



// =====================================================
// GRAFIK CIZ
// =====================================================

function drawChart(
    canvasId,
    values,
    maxValue,
    unit
) {

    const canvas =
        document.getElementById(
            canvasId
        );


    const ctx =
        canvas.getContext(
            "2d"
        );


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


    ctx.lineWidth =
        1;


    for (
        let i = 0;
        i <= 4;
        i++
    ) {

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


    if (
        values.length < 2
    ) {

        return;
    }


    ctx.strokeStyle =
        "#38bdf8";


    ctx.lineWidth =
        3;


    ctx.beginPath();


    values.forEach(
        (
            value,
            index
        ) => {

            const x =
                index /
                (MAX_POINTS - 1) *
                width;


            let normalized =
                value /
                maxValue;


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


            if (
                index === 0
            ) {

                ctx.moveTo(
                    x,
                    y
                );

            }

            else {

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


    ctx.fillStyle =
        "white";


    ctx.font =
        "20px Arial";


    ctx.fillText(

        last.toFixed(1)
        + " "
        + unit,

        15,
        30

    );
}



// =====================================================
// LED BUTONLARI
// =====================================================

function updateLedButtons(
    mode
) {

    [
        "on",
        "off",
        "blink"
    ].forEach(
        name => {

            document
            .getElementById(
                "btn-" + name
            )
            .classList
            .toggle(
                "active",
                name === mode
            );
        }
    );
}



// =====================================================
// GPIO REST API'YE KOMUT GONDER
// =====================================================

async function setLed(
    mode
) {

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

                    method:
                        "POST",

                    headers: {

                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            {
                                mode:
                                    mode
                            }
                        )
                }
            );


        const result =
            await response.json();


        if (
            !response.ok
        ) {

            throw new Error(

                result.error
                ||
                "GPIO hatasi"

            );
        }


        message.textContent =

            "Basarili: GPIO4 modu = "
            +
            result.mode;


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

    catch (
        error
    ) {

        message.textContent =

            "Hata: "
            +
            error.message;
    }
}



// =====================================================
// SISTEM VERILERINI API'DEN CEK
// =====================================================

async function updateDashboard() {

    try {

        const response =
            await fetch(
                "/api/status",
                {
                    cache:
                        "no-store"
                }
            );


        if (
            !response.ok
        ) {

            throw new Error(
                "HTTP hatasi"
            );
        }


        const data =
            await response.json();



        // CPU

        document
        .getElementById(
            "cpu"
        )
        .textContent =

            data.cpu.usage_percent
            +
            " %";


        document
        .getElementById(
            "cpu-bar"
        )
        .style.width =

            data.cpu.usage_percent
            +
            "%";


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
            +
            " %";


        document
        .getElementById(
            "ram-text"
        )
        .textContent =

            data.ram.used_mb
            +
            " MB / "
            +
            data.ram.total_mb
            +
            " MB";


        document
        .getElementById(
            "ram-bar"
        )
        .style.width =

            data.ram.percent
            +
            "%";



        // DISK

        document
        .getElementById(
            "disk-percent"
        )
        .textContent =

            data.disk.percent
            +
            " %";


        document
        .getElementById(
            "disk-text"
        )
        .textContent =

            data.disk.used_gb
            +
            " GB / "
            +
            data.disk.total_gb
            +
            " GB";


        document
        .getElementById(
            "disk-bar"
        )
        .style.width =

            data.disk.percent
            +
            "%";



        // SICAKLIK

        if (
            data.temperature
            === null
        ) {

            document
            .getElementById(
                "temperature"
            )
            .textContent =

                "Bulunamadi";

        }

        else {

            document
            .getElementById(
                "temperature"
            )
            .textContent =

                data.temperature
                .toFixed(1)
                +
                " °C";


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



        // DIGER VERILER

        document
        .getElementById(
            "ip"
        )
        .textContent =
            data.ip;


        document
        .getElementById(
            "wifi"
        )
        .textContent =
            data.wifi;


        document
        .getElementById(
            "hostname"
        )
        .textContent =
            data.hostname;


        document
        .getElementById(
            "uptime"
        )
        .textContent =
            data.uptime.text;


        document
        .getElementById(
            "os"
        )
        .textContent =
            data.os;


        document
        .getElementById(
            "kernel"
        )
        .textContent =
            data.kernel;



        // LED DURUMU

        document
        .getElementById(
            "led-state"
        )
        .textContent =

            data.led.mode
            .toUpperCase();


        updateLedButtons(
            data.led.mode
        );


        document
        .getElementById(
            "connection"
        )
        .textContent =

            "API ONLINE";

    }

    catch (
        error
    ) {

        document
        .getElementById(
            "connection"
        )
        .textContent =

            "API BAGLANTI HATASI";


        console.error(
            error
        );
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
'''


# =========================================================
# HTTP SERVER
# =========================================================

class PanelHandler(
    BaseHTTPRequestHandler
):


    # -----------------------------------------------------
    # JSON CEVABI GONDER
    # -----------------------------------------------------

    def send_json(
        self,
        status_code,
        data
    ):

        payload = (
            json.dumps(
                data
            )
            .encode(
                "utf-8"
            )
        )


        self.send_response(
            status_code
        )


        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )


        self.send_header(
            "Cache-Control",
            "no-store"
        )


        self.end_headers()


        self.wfile.write(
            payload
        )


    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    def do_GET(
        self
    ):


        # ANA SAYFA

        if (
            self.path == "/"
        ):

            self.send_response(
                200
            )


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

                HTML_PAGE.encode(
                    "utf-8"
                )

            )



        # SISTEM API

        elif (
            self.path ==
            "/api/status"
        ):

            self.send_json(

                200,

                get_system_data()

            )



        # FAVICON

        elif (
            self.path ==
            "/favicon.ico"
        ):

            self.send_response(
                204
            )

            self.end_headers()



        # BULUNAMADI

        else:

            self.send_json(

                404,

                {
                    "error":
                        "Not Found"
                }

            )


    # -----------------------------------------------------
    # POST
    # -----------------------------------------------------

    def do_POST(
        self
    ):


        # Sadece LED API'sini kabul et

        if (
            self.path !=
            "/api/led"
        ):

            self.send_json(

                404,

                {
                    "error":
                        "Not Found"
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


            body = (
                self.rfile.read(
                    length
                )
            )


            request_data = (
                json.loads(
                    body.decode(
                        "utf-8"
                    )
                )
            )


            mode = (
                request_data.get(
                    "mode"
                )
            )


            set_led_mode(
                mode
            )


            self.send_json(

                200,

                {

                    "ok":
                        True,

                    "mode":
                        mode,

                    "gpio":
                        GPIO_LINE
                }

            )


        except (
            ValueError,
            json.JSONDecodeError
        ) as e:


            self.send_json(

                400,

                {

                    "ok":
                        False,

                    "error":
                        str(e)
                }

            )


        except Exception as e:


            self.send_json(

                500,

                {

                    "ok":
                        False,

                    "error":
                        str(e)
                }

            )


# =========================================================
# PROGRAM BASLANGICI
# =========================================================

if __name__ == "__main__":


    # Program açıldığında
    # LED'i güvenli olarak kapalı tut.

    try:

        set_led_mode(
            "off"
        )

        print(
            f"GPIO baslangic durumu: "
            f"{GPIO_LINE}=OFF"
        )

    except Exception as e:

        print(
            "UYARI: GPIO baslatilamadi:",
            e
        )


    server = (
        ThreadingHTTPServer(
            (
                "0.0.0.0",
                PORT
            ),
            PanelHandler
        )
    )


    print(
        "Gemstone V5 baslatildi."
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
