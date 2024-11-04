# Import necessary modules for the web server
from flask import Flask, render_template, request, redirect, url_for, flash
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import socket
import subprocess
import os
import asyncio
import sqlite3
from datetime import datetime
import secrets

# Import custom module
from turn_lights import control_wiz_light, get_light_status
from smart_home import is_valid_mac, is_valid_ip, execute_command, remote_shutdown_func

# Configuration
wizlight_ip = "192.168.87.102"
remote_pc_ip = "192.168.87.3"
remote_pc_mac = "24:4b:fe:93:78:f8"
remote_pc_user = "jvolp"
watering_db = 'db/watering.db'

app = Flask(__name__)

# Function to ensure the watering table exists
def create_watering_table():
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




def get_data_from_db(number_of_rows=10):
    query = "SELECT * FROM growdata ORDER BY date_time_str DESC;"
    datetime, temperature, humidity, moisture = [], [], [], []
    try:
        conn = sqlite3.connect('db/data.db')
        curs = conn.cursor()
        curs.execute(query)
        rows = curs.fetchmany(number_of_rows)
        for row in rows:
            datetime.append(row[0])
            temperature.append(row[2])
            humidity.append(row[4])
            moisture.append(row[1])
    except Exception as e:
        print("Error occurred while fetching data from the database.")
        print(f"Error: {e}")
    finally:
        curs.close()
        conn.close()
    return datetime, temperature, humidity, moisture

def graph_db_data(sensor_type="temp"):
    timestamps, temperature_data, humidity_data, moisture = get_data_from_db(24)  # Ensure your DB returns a third value
    timestamps = [str(t)[:19] for t in timestamps]  # Remove milliseconds
    fig, ax = plt.subplots(figsize=(10, 8))
    plt.style.use('dark_background')

    if sensor_type == "temp":
        ax.plot(timestamps, temperature_data, label="Temperature", linestyle="-", marker="o", color="r")
        ax.set_title("Temperature")
        ax.set_ylabel("Temperature")
        #ax.set_ylim(22, 28)
        ax.fill_between(timestamps, temperature_data, color="r", alpha=0.1)
    elif sensor_type == "hum":
        ax.plot(timestamps, humidity_data, label="Humidity", linestyle="-", marker="o", color="b")
        ax.set_title("Humidity")
        ax.set_ylabel("Humidity")
        ax.fill_between(timestamps, humidity_data, color='b', alpha=0.1)
    elif sensor_type == "moisture":
        ax.plot(timestamps, moisture, label="Moisture", linestyle="-", marker="o", color="g")
        ax.set_title("Moisture")
        ax.set_ylabel("Moisture")
        ax.fill_between(timestamps, moisture, color='g', alpha=0.1)
    else:
        print(f"Invalid data type: {sensor_type}")
        return sensor_type

    ax.set_xlabel("Time")
    ax.tick_params(axis="x", rotation=45)
    ax.invert_xaxis()  # Invert X axis to show the latest data on the right
    fig.tight_layout()

    buf = BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    data = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"<img class='img-fluid' src='data:image/png;base64,{data}'/>"

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/temperature")
def stue():
    return render_template(
        "temperature.html",
        data_img=graph_db_data("temp"),
        data_img2=graph_db_data("hum"),
        data_img3=graph_db_data("moisture"),
    )


@app.route("/lights", methods=["GET", "POST"])
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
def show_photo():
    # Get the filename of the photo
    photo_filename = request.args.get('photo_filename')
    
    # Pass the correct URL for the static photo
    photo_url = url_for('static', filename=f'{photo_filename}')
    return render_template('show_photo.html', photo_url=photo_url)


@app.route('/photo')
def photo():
    return render_template('photo.html')

IMAGE_DIR = '/home/javier/SmartHome/static'
# Route to list images in a gallery
@app.route('/gallery', methods=['GET', 'POST'])
def gallery():
    images = sorted([img for img in os.listdir(IMAGE_DIR) if not img.startswith('.')], reverse=True)  # Exclude hidden files
    filtered_images = images
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date and end_date:
        # Filter images based on the date in the filename (assuming filename includes timestamp like YYYYMMDD_HHMMSS)
        filtered_images = [img for img in images if start_date <= img[:8] <= end_date]
    
    return render_template('gallery.html', images=filtered_images)

@app.route('/slideshow/<filename>')
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
def remote_power():
    return render_template("remote_power.html", remote_pc_ip=remote_pc_ip, remote_pc_mac=remote_pc_mac)


# Route to handle displaying and recording watering
@app.route('/watering', methods=['GET', 'POST'])
def watering():
    create_watering_table()  # Ensure the table exists

    if request.method == 'POST':
        amount_ml = request.form.get('amount_ml') or None
        if amount_ml:

                amount_ml = int(amount_ml)
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






















app.secret_key = secrets.token_hex(16)

app.run(debug=True, host="0.0.0.0", port=5000)
