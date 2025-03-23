# 🌱 SmartGrow – Automated IoT Grow System

SmartGrow is a full-stack, IoT-powered grow monitoring and automation system built for indoor plant cultivation. It integrates hardware sensors (ESP32, Raspberry Pi), MQTT communication, a responsive web dashboard, and automation tools for fans, lights, watering, and environmental monitoring.

* * *

## 🚀 Features

### 📡 MQTT-Driven IoT System

-   Two ESP32 nodes (grow tent + drying area) with soil and air sensors.
-   MQTT topics to send and receive commands and sensor data.
-   OTA updates for ESP32 and MicroPython logic via HTTP.

### 📈 Sensor Monitoring

-   Real-time and historical data:
    -   Soil moisture
    -   Soil temperature (DS18B20)
    -   Ambient temperature & humidity (DHT22/DHT11)
-   Responsive web dashboard and data visualizations.

### 💨 Environmental Controls

-   Fan control (top fan, bottom fan, dry fan) with speed adjustment.
-   Water pump control.
-   WiZ light control via Python script.
-   Smart plug control via MQTT (Shelly Plug RPC).
-   Scheduling for automatic toggles.

### 📷 Camera & Gallery

-   Trigger remote camera to take snapshots twice daily.
-   View gallery with pagination, date filtering, and fullscreen slideshow.
-   Ideal for time-lapse growth tracking.

### 🔐 User Management

-   Flask-Login system with registration, login/logout.
-   Secure storage via SQLite (hashed passwords).

### ⚙️ Automation & Cron

-   In-browser Crontab editor for scheduling tasks.
-   Supports both standard and special cron jobs.

### 📊 Dashboard

-   Central view of all system states and latest sensor values.
-   Last watering log, light/fan statuses, and plug state.
* * *

## 🧰 Technologies Used

| Component | Stack |
| --- | --- |
| Frontend | HTML, Bootstrap 5, Jinja2 Templates |
| Backend | Flask (Python), SQLite |
| Hardware | ESP32, DHT22, DS18B20, Capacitive Soil Sensor |
| Messaging Protocol | MQTT (paho-mqtt) |
| Camera Control | Flask API for Raspberry Pi Camera |
| OTA | MicroPython + urequests + MQTT |

* * *

## 🔌 MQTT Topics

| Node | Publish Topic | Subscribe Topic |
| --- | --- | --- |
| Grow Tent | `grow/data` | `grow/control` |
| Dry Room | `dry/data` | `dry/control` |
| Web App | Subscribes/publishes as needed across both |  |

* * *

## 📷 Example Workflow

1.  ESP32 reads soil and climate data every 30 minutes.
2.  Sends readings via MQTT to a local broker.
3.  Raspberry Pi logs data into SQLite and forwards to cloud broker.
4.  Web app displays graphs and gallery.
5.  Fans, pumps, and lights can be controlled from UI or via schedules.
* * *

## 🔐 Access Control

-   Only authenticated users can control or view the system.
-   Admin panel includes watering logs, cron job manager, and power actions (Wake-on-LAN / remote shutdown).
* * *

## 👨‍💻 Author

Javier Alejandro Volpe  | 
🌍 Denmark | 🍃 IoT Enthusiast
