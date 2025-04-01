SmartGrow -- Automated IoT Grow System
=====================================

SmartGrow is an IoT-powered, full-stack system for monitoring and automating indoor plant cultivation. The system integrates sensors, MQTT communication, and a web dashboard, allowing users to monitor environmental conditions and control various devices like fans, pumps, and lights.

* * * * *

?? Features
-----------

### ?? MQTT-Driven IoT System

-   Two ESP32 nodes (grow tent and drying area) with soil and air sensors.

-   MQTT topics for sending and receiving sensor data and commands.

-   OTA updates for ESP32 and MicroPython logic via HTTP.

### ?? Sensor Monitoring

-   Real-time and historical data for:

    -   Soil moisture

    -   Soil temperature (DS18B20)

    -   Ambient temperature and humidity (DHT22/DHT11)

-   Visualizations through a responsive web dashboard.

### ?? Environmental Controls

-   Fan control (top fan, bottom fan, dry fan) with speed adjustment.

-   Water pump control.

-   WiZ light control via Python script.

-   Smart plug control via MQTT (Shelly Plug RPC).

-   Scheduling for automatic toggles.

### ?? Camera & Gallery

-   Remote camera triggers for snapshots twice a day.

-   View and filter images in the gallery with pagination and slideshow functionality.

-   Ideal for time-lapse plant growth tracking.

### ?? User Management

-   Secure login system via Flask-Login with SQLite-backed user data.

-   Passwords are hashed for security.

### ?? Automation & Cron

-   In-browser Crontab editor for scheduling tasks.

-   Support for both standard cron jobs and special jobs (e.g., `@reboot`).

### ?? Dashboard

-   A central view displaying system states and sensor data.

-   Watering logs, fan/pump statuses, and plug states are visible in real time.

* * * * *

?? Technologies Used
--------------------

| **Component** | **Stack** |
| --- | --- |
| **Frontend** | HTML, Bootstrap 5, Jinja2 Templates |
| **Backend** | Flask (Python), SQLite |
| **Hardware** | ESP32, DHT22, DS18B20, Capacitive Soil Sensor |
| **Messaging Protocol** | MQTT (paho-mqtt) |
| **Camera Control** | Flask API for Raspberry Pi Camera |
| **OTA** | MicroPython + urequests + MQTT |

* * * * *

?? MQTT Topics
--------------

| **Node** | **Publish Topic** | **Subscribe Topic** |
| --- | --- | --- |
| Grow Tent | `grow/data` | `grow/control` |
| Dry Room | `dry/data` | `dry/control` |
| Web App | Publishes/subscribes as needed across both |  |

* * * * *

?? Example Workflow
-------------------

1.  **ESP32** reads sensor data every 30 minutes and sends it via MQTT to the local broker.

2.  **Raspberry Pi** logs the data into an SQLite database and forwards it to the cloud broker.

3.  **Web App** displays data visualizations and the image gallery.

4.  **Control** fans, pumps, and lights via the web interface or set schedules for automation.

* * * * *

?? Access Control
-----------------

-   Only authenticated users can access system controls and view the data.

-   The admin panel includes:

    -   Watering logs

    -   Cron job management

    -   Power actions like Wake-on-LAN and remote shutdown.

* * * * *

?? Installation
---------------

### Prerequisites

-   **Python** 3.7+

-   **Flask**

-   **SQLite**

-   **paho-mqtt**

-   **MicroPython** (for ESP32)

### Steps to Run

1.  **Clone the repository:**

    bash

    Copy

    `git clone https://github.com/JavierVolpe/SmartGrow.git
    cd smartgrow`

2.  **Install dependencies:**

    bash

    Copy

    `pip install -r requirements.txt`

3.  **Run the Flask app:**

    bash

    Copy

    `python app.py`

4.  **Flash the ESP32:** Follow the instructions in the repository's `README` to flash the ESP32 with the required MicroPython firmware and the correct code.

* * * * *

??? Customization
-----------------

### Cron Jobs

-   Use the built-in **cron editor** to schedule regular tasks like data syncing or device control.

### Sensor Calibration

-   Adjust the soil moisture sensor thresholds (`DRY_SOIL`, `WET_SOIL`) and other sensor parameters to fit your environment.

### OTA Updates

-   The ESP32 can perform OTA updates via HTTP to update the firmware remotely. Customize the OTA URL in `config.py`.


????? Author
------------

**Javier Alejandro Volpe**\
?? Denmark | ?? IoT Enthusiast

* * * * *
