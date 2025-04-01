🌱 SmartGrow -- Automated IoT Grow System
=====================================

SmartGrow is an IoT-powered, full-stack system for monitoring and automating indoor plant cultivation. The system integrates sensors, MQTT communication, and a web dashboard, allowing users to monitor environmental conditions and control various devices like fans, pumps, and lights.

* * * * *

🚀 Features
-----------

### 📡 **MQTT-Powered IoT Nodes**

-   🌿 **Grow Tent and Drying Room Nodes:** ESP32-based with integrated soil and air sensors.

-   🔄 **MQTT Communication:** Real-time data and command exchange.

-   🌐 **OTA Updates:** Update ESP32 nodes remotely via HTTP.

### 📈 **Real-Time Sensor Monitoring**

-   💧 **Soil Moisture**

-   🌡️ **Soil Temperature (DS18B20)**

-   🌤️ **Ambient Temperature & Humidity (DHT22/DHT11)**

-   📊 Responsive dashboard visualizations

### 💨 **Comprehensive Environmental Controls**

-   🌬️ **Fan Control:** Adjustable speed and automation for top, bottom, and drying fans.

-   🚰 **Water Pump Management**

-   💡 **WiZ Smart Lights Integration**

-   🔌 **Smart Plug Management via MQTT (Shelly Plug RPC)**

-   📅 **Automated Scheduling**

### 📷 **Camera & Interactive Gallery**

-   📸 **Twice Daily Snapshots:** Perfect for growth tracking.

-   🖼️ **Gallery View:** Pagination, filtering by date, and slideshow mode.

### 🔐 **Robust User Management**

-   👤 Secure user login system with Flask-Login.

-   🗄️ Passwords securely hashed and stored using SQLite.

### ⚙️ **Advanced Automation & Cron Management**

-   🕒 **Web-based Cron Editor:** Easily schedule tasks.

-   ✨ Supports special cron jobs (e.g., `@reboot`).

### 📊 **Centralized Dashboard**

-   📍 Quick view of current system status.

-   🌱 Recent watering logs, sensor values, fan, pump, and plug statuses.

* * * * *

🧰 Tech Stack
-------------

| Component | Technologies |
| 🎨 **Frontend** | HTML, Bootstrap 5, Jinja2 |
| ⚙️ **Backend** | Python Flask, SQLite |
| 🛠️ **Hardware** | ESP32, DHT22, DS18B20, Capacitive Soil Sensor |
| 📡 **Messaging** | MQTT (paho-mqtt) |
| 📷 **Camera Control** | Flask API, Raspberry Pi Camera |
| 🔄 **OTA** | MicroPython, MQTT, urequests |

* * * * *

🔌 MQTT Communication
---------------------

| Node | Publish Topic | Subscribe Topic |
| 🌿 Grow | `grow/data` | `grow/control` |
| 🍃 Dry | `dry/data` | `dry/control` |

* * * * *

🗺️ Workflow Example
--------------------

1.  🌡️ **ESP32** collects sensor data every 30 minutes.

2.  🔄 Sends data via **MQTT** to the local broker.

3.  💻 **Raspberry Pi** logs and forwards data to cloud.

4.  📈 Web app visualizes data and manages automation.

* * * * *

🔒 Secure Access
----------------

-   ✅ Authenticated-only access to controls and data.

-   🔑 Admin panel with comprehensive management tools (watering logs, cron jobs, power actions).

* * * * *

📂 Installation Guide
---------------------

### 🛠️ **Prerequisites**

-   Python 3.7+

-   Flask

-   SQLite

-   paho-mqtt

-   MicroPython (for ESP32)

### 📥 **Setup Instructions**

```
git clone https://github.com/JavierVolpe/SmartGrow.git
cd SmartGrow
pip install -r requirements.txt
python app.py
```

**ESP32 Flashing:**

-   Refer to the provided firmware instructions within the repository.

* * * * *

⚙️ Customizations
-----------------

-   🕒 **Cron Jobs:** Schedule recurring tasks easily through the web-based cron editor.

-   ⚖️ **Sensor Calibration:** Modify soil moisture thresholds to suit your environment.

-   🌐 **OTA Updates:** Configure OTA firmware URLs in `config.py`.

* * * * *

🤝 Contributing & Feedback
--------------------------

-   🐞 Report issues and suggest features by creating issues.

-   💡 Submit enhancements via pull requests.

* * * * *

👨‍💻 Author
------------

**Javier Alejandro Volpe**

🌍 Denmark | 🍃 IoT Enthusiast
