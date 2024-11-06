# Flask and Flask-Login imports
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

# Security and password hashing
from werkzeug.security import generate_password_hash, check_password_hash

# Data visualization and image handling imports
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from io import BytesIO
import base64

# System and OS-level imports
import socket
import subprocess
import os
import asyncio
import sqlite3

# Date and time handling
from datetime import datetime

# Secret key generation for session management
import secrets

# Import custom modules for specific functionalities
from turn_lights import control_wiz_light, get_light_status
from smart_home import is_valid_mac, is_valid_ip, execute_command, remote_shutdown_func
import paho.mqtt.client as mqtt

# TODO:
# 1. Wizlight: make it optional
# 2. Upload code for the ESP32




# Configuration
wizlight_ip = "192.168.87.102"
remote_pc_ip = "192.168.87.3"
remote_pc_mac = "24:4b:fe:93:78:f8"
remote_pc_user = "jvolp"
watering_db = 'db/watering.db'

app = Flask(__name__)


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

# Load user from database
@login_manager.user_loader
def load_user(user_id):
    try:
        conn = sqlite3.connect('db/users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
    except Exception as e:
        print(f"Error loading user: {e}")

    if user:
        return User(id=user[0], username=user[1], password=user[2])
    return None






# Function to ensure the watering table exists
def create_watering_table():
    try:
        conn = sqlite3.connect('db/watering.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS watering_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                amount_ml INTEGER
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error creating watering table: {e}")
        return False




def graph_db_data(sensor_type="temp", number_of_rows=24):
    # Fetch data from the database
    query = "SELECT * FROM growdata ORDER BY date_time_str DESC;"
    # send_update(moisture, temperature_ds, temperature_dht, int(humidity)) 
    timestamps, temperature_data, humidity_data, moisture_data, temp_dht = [], [], [], [], []
    try:
        conn = sqlite3.connect('db/data.db')
        curs = conn.cursor()
        curs.execute(query)
        rows = curs.fetchmany(number_of_rows)
        for row in rows:
            timestamps.append(str(row[0])[:19])  # Remove milliseconds
            temperature_data.append(row[2]) # temperature_ds
            temp_dht.append(row[3]) # temperature_dht
            humidity_data.append(row[4])
            moisture_data.append(row[1])
    except Exception as e:
        print("Error occurred while fetching data from the database.")
        print(f"Error: {e}")
        return ""
    finally:
        curs.close()
        conn.close()

    # Create the plot
    fig, ax = plt.subplots(figsize=(10, 8))
    plt.style.use('dark_background')

    if sensor_type == "temp":
        data_to_plot = temperature_data
        label = "Temperature"
        color = "r"
        y_label = "Temperature (°C)"  # You can adjust the units if necessary
    elif sensor_type == "hum":
        data_to_plot = humidity_data
        label = "Humidity"
        color = "b"
        y_label = "Humidity (%)"
    elif sensor_type == "moisture":
        data_to_plot = moisture_data
        label = "Moisture"
        color = "g"
        y_label = "Soil Moisture (%)"
    elif sensor_type == "temp_dht":
        data_to_plot = temp_dht
        label = "Ambient Temperature"
        color = "y"
        y_label = "Ambient Temperature (°C)"
    else:
        print(f"Invalid data type: {sensor_type}")
        return ""

    ax.plot(timestamps, data_to_plot, label=label, linestyle="-", marker="o", color=color)
    ax.set_title(f"{label} Over Time")
    ax.set_ylabel(y_label)
    ax.fill_between(timestamps, data_to_plot, color=color, alpha=0.1)

    ax.set_xlabel("Time")
    ax.tick_params(axis="x", rotation=45)
    ax.invert_xaxis()  # Show the latest data on the right
    fig.tight_layout()

    # Convert the plot to a base64-encoded string
    buf = BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    data = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"<img class='img-fluid' src='data:image/png;base64,{data}'/>"

@app.route("/")
def index():
    return render_template("index.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        # Save user to the database
        conn = sqlite3.connect('db/users.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
        conn.commit()
        conn.close()
        flash('Registration successful. You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('db/users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            user_obj = User(id=user[0], username=user[1], password=user[2])
            login_user(user_obj)
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))





def publish_mqtt_message(message, success_msg, error_msg):
    try:
        mqtt_client = mqtt.Client()
        mqtt_client.connect('192.168.87.2', 1883, 60)
        mqtt_client.publish('javier/growcontrol', message)
        mqtt_client.disconnect()
        flash(success_msg, 'success')
    except Exception as e:
        flash(f'{error_msg}: {e}', 'danger')
    return redirect(url_for('temperature'))

""" @app.route("/temperature")
@login_required
def temperature():
    return render_template(
        "temperature.html",
        data_img=graph_db_data("temp", 24),
        data_img2=graph_db_data("hum"),
        data_img3=graph_db_data("moisture"), )"""
    

@app.route("/temperature")
@login_required
def temperature():
    return render_template(
        "temperature.html",
        data_img=graph_db_data("temp", 24),
        data_img2=graph_db_data("hum", 24),
        data_img3=graph_db_data("moisture", 24),
        data_img4=graph_db_data("temp_dht", 24),
    )

@app.route('/send_update', methods=['POST'])
def send_update():
    return publish_mqtt_message('send_update', 'Update request sent successfully.', 'Failed to send update request')



@app.route("/lights", methods=["GET", "POST"])
@login_required
def lights():
    light_status = asyncio.run(get_light_status(wizlight_ip))
    if request.method == "POST":
        light_status = request.form.get("lightStatus")
        if light_status == "ON":
            asyncio.run(control_wiz_light(wizlight_ip, "ON"))
        elif light_status == "OFF":
            asyncio.run(control_wiz_light(wizlight_ip, "OFF"))

        else:
            print(f"Invalid lightStatus: {light_status}")

    return render_template("lights.html", light_status=light_status)


@app.route('/take_photo', methods=['POST'])
@login_required
def take_photo():
    # Use the format for filenames that works well with the filesystem and Flask static files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    photo_filename = f'{timestamp}.jpg'
    photo_path = f'/home/javier/SmartHome/static/{photo_filename}'  # Save photo in the static/images folder

    # Take the photo and save it
    os.system(f'rpicam-jpeg -o {photo_path} --rotation 180')

    # Redirect to show_photo with the correct static URL
    return redirect(url_for('show_photo', photo_filename=photo_filename))


@app.route('/show_photo')
@login_required
def show_photo():
    # Get the filename of the photo
    photo_filename = request.args.get('photo_filename')
    
    # Pass the correct URL for the static photo
    photo_url = url_for('static', filename=f'{photo_filename}')
    return render_template('show_photo.html', photo_url=photo_url)


@app.route('/photo')
@login_required
def photo():
    return render_template('photo.html')

IMAGE_DIR = '/home/javier/SmartHome/static'
# Route to list images in a gallery


@app.route('/gallery', defaults={'page': 1}, methods=['GET', 'POST'])
@app.route('/gallery/page/<int:page>', methods=['GET', 'POST'])
@login_required
def gallery(page):
    images = sorted([img for img in os.listdir(IMAGE_DIR) if not img.startswith('.')], reverse=True)  # Exclude hidden files
    filtered_images = images

    # Filter images based on date in the filename (assuming format YYYYMMDD_HHMMSS)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if start_date and end_date:
        filtered_images = [img for img in images if start_date <= img[:8] <= end_date]

    # Pagination logic
    images_per_page = 12
    total_images = len(filtered_images)
    start_index = (page - 1) * images_per_page
    end_index = start_index + images_per_page
    paginated_images = filtered_images[start_index:end_index]

    # Determine if there are previous and next pages
    has_prev = page > 1
    has_next = end_index < total_images

    return render_template(
        'gallery.html',
        images=paginated_images,
        page=page,
        has_prev=has_prev,
        has_next=has_next
    )

@app.route('/slideshow/<filename>')
@login_required
def slideshow(filename):
    # Get the list of images, excluding hidden files
    images = [img for img in sorted(os.listdir('static')) if not img.startswith('.')]  # Exclude hidden files
    current_index = images.index(filename)

    # Find the previous and next image filenames
    prev_image = images[current_index - 1] if current_index > 0 else images[-1]
    next_image = images[(current_index + 1) % len(images)]  # Wrap around to the first image if at the last image

    # Extract the timestamp from the filename (assuming format YYYYMMDD_HHMMSS.jpg)
    timestamp_str = filename.split('.')[0]  # Strip the .jpg
    picture_datetime = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S').strftime('%B %d, %Y at %H:%M:%S')

    # Render the template with image and navigation
    return render_template('slideshow.html', image=f'{filename}', prev_image=prev_image, next_image=next_image, picture_datetime=picture_datetime)


@app.route("/remote_wakeup", methods=["GET", "POST"])
@login_required
def wol():
    if request.method == "POST":
        mac_address = request.form.get("macAddress")
        if is_valid_mac(mac_address):
            result = execute_command(f"sudo etherwake -i wlan0 {mac_address}")
        else:
            result = "Error: Invalid MAC address"
    else: # TODO: Check why is it jumping to this else
        result = None
        if is_valid_mac(remote_pc_mac):
            result = execute_command(f"sudo etherwake -i wlan0 {remote_pc_mac}")
        else:
            result = "Error: Invalid MAC address"
    return render_template("remote_power.html", remote_pc_ip=remote_pc_ip, remote_pc_mac=remote_pc_mac)


@app.route("/remote_shutdown", methods=["GET", "POST"])
@login_required
def remote_shutdown():

    if request.method == "POST":
        ip_address = request.form.get("ipAddress")
        if is_valid_ip(ip_address):
            if remote_shutdown_func(ip_address):
                result = f"Result: Remote shutdown command sent to {ip_address}"
            else:
                result = f"Error: Remote shutdown command failed for {ip_address}"
        else:
            result = "Error: Invalid IP address"
    else:
        ...
        result = ""
    return render_template("remote_power.html", remote_pc_ip=remote_pc_ip, remote_pc_mac=remote_pc_mac, result=result)



@app.route("/remote_power")
@login_required
def remote_power():
    return render_template("remote_power.html", remote_pc_ip=remote_pc_ip, remote_pc_mac=remote_pc_mac)


# Route to handle displaying and recording watering
@app.route('/watering', methods=['GET', 'POST'])
@login_required
def watering():
    create_watering_table()  # Ensure the table exists

    if request.method == 'POST':
        amount_ml = request.form.get('amount_ml') or None
        if amount_ml:
                amount_ml = int(amount_ml)
                if amount_ml < 0:
                    flash('Amount must be a positive number.', 'danger')
                    return redirect(url_for('watering'))


        else: 
            amount_ml = None
        try:        

                # Connect to the database
                conn = sqlite3.connect(watering_db)
                cursor = conn.cursor()

                time_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                # Insert the new watering record
                cursor.execute('INSERT INTO watering_log (timestamp, amount_ml) VALUES (?, ?)', (time_now, amount_ml))
                conn.commit()
                conn.close()

                # Flash a success message
                flash('Watering record added successfully.', 'success')
        except Exception as e:
            print(f"Error: {e}")
            flash('Error adding watering record. Please try again.', 'danger')

        return redirect(url_for('watering'))


    # Fetch watering logs
    conn = sqlite3.connect(watering_db)
    cursor = conn.cursor()
    cursor.execute('SELECT timestamp, amount_ml, id FROM watering_log ORDER BY timestamp DESC')
    logs = cursor.fetchall()
    conn.close()


    return render_template('watering.html', logs=logs)


@app.route('/delete_watering/<int:log_id>', methods=['POST'])
@login_required
def delete_watering(log_id):
    # Connect to the database
    conn = sqlite3.connect(watering_db)
    cursor = conn.cursor()

    # Delete the record with the given id
    cursor.execute('DELETE FROM watering_log WHERE id = ?', (log_id,))
    conn.commit()
    conn.close()

    # Flash a success message
    flash('Watering record deleted successfully.', 'success')

    return redirect(url_for('watering'))

# Route to handle the "Start Fan" button
@app.route('/start_fan', methods=['POST'])
@login_required
def start_fan():
    return publish_mqtt_message('start_fan', 'Fan started successfully.', 'Failed to start fan')

# Route to handle the "Stop Fan" button
@app.route('/stop_fan', methods=['POST'])
@login_required
def stop_fan():
    return publish_mqtt_message('stop_fan', 'Fan stopped successfully.', 'Failed to stop fan')





















app.secret_key = secrets.token_hex(16)

app.run(debug=True, host="0.0.0.0", port=5000)
