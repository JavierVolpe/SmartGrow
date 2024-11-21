# Smart Grow House Control System

This is a smart system designed to monitor and control a grow house using IoT devices. The system integrates various sensors, an ESP32 microcontroller, and a Raspberry Pi, all controlled via a Flask-based web interface. The system is capable of collecting environmental data (temperature, humidity, soil moisture) and taking pictures of the grow house, while allowing users to control devices like fans and lights remotely.

## Components

- **ESP32**: Monitors environmental conditions (temperature, humidity, soil moisture) using sensors such as DS18B20, DHT22, and an analog soil moisture sensor.
- **Raspberry Pi**: Handles the camera for daily picture taking, processes sensor data, and hosts the Flask web interface.
- **MQTT Broker**: Facilitates communication between the ESP32 and Raspberry Pi to transmit sensor data and control messages.
- **Flask Web Interface**: A web interface to view sensor data, control devices, and take pictures remotely.

## Features

- **Environmental Monitoring**: Collects and visualizes temperature, humidity, and soil moisture data in real-time.
- **Daily Photography**: The Raspberry Pi camera takes pictures of the grow house twice a day.
- **Device Control**: Allows control of IoT devices like fans and lights via the web interface.
- **Data Visualization**: Graphs show data trends for temperature, humidity, and soil moisture.
- **User Authentication**: A secure login system for managing and controlling the grow house.

## Setup

### Prerequisites

- Python 3.x
- Flask
- SQLite
- Paho MQTT
- Matplotlib
- MicroPython on ESP32

### Installing Dependencies

1. Clone the repository:

    ```bash
    git clone https://github.com/JavierVolpe/SmartGrow/SmartGrow.git
    cd SmartGrow
    ```

2. Install required Python libraries:

    ```bash
    pip install -r requirements.txt
    ```

### ESP32 Setup

1. Flash the ESP32 with the provided MicroPython script (located in `main.py`) to start reading sensor data and publishing it via MQTT.
2. Connect your ESP32 to the same network as your Raspberry Pi.

### Raspberry Pi Setup

1. Ensure your Raspberry Pi is connected to the same network as the ESP32 and the MQTT broker.
2. Configure your MQTT broker settings in the `config.py` file.
3. Run the Flask web app:

    ```bash
    python app.py
    ```

4. Access the web interface by navigating to `http://<raspberry_pi_ip>:5000` in your browser.

### Web Interface

- **Home Page**: Displays real-time data from the sensors (temperature, humidity, soil moisture) and the latest image from the camera.
- **Temperature and Humidity**: View graphs of temperature, humidity, and soil moisture from the past 24 hours.
- **Device Control**: Control the fan, lights, and smart plugs.
- **Gallery**: View a collection of photos taken by the Raspberry Pi camera.

## Configuration

- **MQTT Configuration**: Set the MQTT server and topics in `config.py` under `Config` class.
- **Camera Setup**: The camera is controlled using `rpicam-jpeg` (ensure it's installed and accessible from the Raspberry Pi).
- **User Database**: The system uses SQLite to manage users. Add users via the Flask web interface.

## Usage

1. **Login**: Register a new user or login with existing credentials.
2. **Control Devices**: Turn on/off the fan, lights, and control smart plugs.
3. **Monitor Environment**: View real-time sensor data and check graphs for environmental trends.
4. **Take Photos**: Trigger the Raspberry Pi to take a photo and view it instantly.

## MQTT Topics

- **Publishing Sensor Data**: `javier/growdata`
- **Device Control**: `javier/growcontrol`
- **Watering Event**: `javier/growwatering`

## Contributing

Feel free to fork this project and contribute to it by submitting issues or pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Note**: Remember to adjust all paths, IP addresses, and configurations to suit your environment before deploying.
