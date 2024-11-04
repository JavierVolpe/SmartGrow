SmartGrow
=========

SmartGrow is a comprehensive home automation and monitoring system built using Flask, designed to manage and track various aspects of a smart indoor garden. The application provides functionalities for temperature and humidity monitoring, watering logs, camera controls, light management, and remote power operations.

Features
--------

### 1\. **Temperature and Humidity Monitoring**

-   Displays real-time temperature, humidity, and soil moisture data.

-   Graphs are generated from the latest 24 data points in the database, allowing users to visualize changes over time.

### 2\. **Light Control**

-   Allows users to remotely control smart lights connected via a specific IP.

-   Supports turning lights on and off from the user interface.

### 3\. **Camera Functionality**

-   Users can capture images using the camera connected to the Raspberry Pi.

-   The captured images are stored in a designated static directory and can be viewed through a dedicated photo page.

### 4\. **Gallery and Slideshow**

-   The app includes a gallery that displays images in a grid layout with pagination (12 images per page).

-   Users can navigate between images in a slideshow mode and view timestamps of when each picture was taken.

### 5\. **Remote Power Operations**

-   Provides Wake-on-LAN (WOL) functionality to wake up a device using its MAC address.

-   Supports remote shutdown operations by specifying the IP address of the target device.

### 6\. **Watering Management**

-   Users can log watering activities with timestamps and the amount of water used.

-   Displays a table of past watering logs with options to delete entries.

Installation
------------

1.  **Clone the Repository**:

    ```
    git clone https://github.com/JavierVolpe/SmartGrow
    cd SmartGrow
    ```

2.  **Install Dependencies**: Ensure you have Python and Flask installed. You can use `pip` to install necessary packages:

    ```
    pip install -r requirements.txt
    ```

3.  **Set Up the Database**: Create any required database tables by running the application once or manually executing the database creation logic.

4.  **Run the Application**:

    ```
    python app.py
    ```

    The app will run on `http://0.0.0.0:5000` by default.

Folder Structure
----------------

-   **app.py**: Main application script containing all route and business logic.

-   **templates/**: Contains HTML templates for the Flask app.

-   **static/**: Directory where captured images and other static assets are stored.

-   **db/**: Stores the SQLite databases for watering logs and other sensor data.

-   **turn_lights.py** and **smart_home.py**: Custom modules for light control and remote power operations.

Usage
-----

-   Navigate to the root URL to access the main dashboard.

-   Use the **Temperature** section to view current temperature, humidity, and moisture levels.

-   Go to **Lights** to control the smart lighting system.

-   Visit **Photo** to take pictures and **Gallery** to browse them.

-   Access **Remote Power** for power operations like waking up or shutting down remote devices.

-   Log and view watering records in the **Watering** section.

Technologies Used
-----------------

-   **Python**

-   **Flask**

-   **SQLite**

-   **Matplotlib** for data visualization

-   **HTML/CSS** with **Bootstrap** for responsive design

Security
--------

-   The app uses a randomly generated secret key for session management:

    ```
    app.secret_key = secrets.token_hex(16)
    ```

Future Enhancements
-------------------

-   Integration with more IoT devices for broader home automation.

-   Enhanced data visualization options.

-   User authentication for added security.

License
-------

This project is licensed under the MIT License.
