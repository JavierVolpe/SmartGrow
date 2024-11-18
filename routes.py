# Standard library imports
import os
import sqlite3
import asyncio
from datetime import datetime

# Third-party imports
from flask import render_template, request, redirect, url_for, flash, session
from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash
import paho.mqtt.client as mqtt

# Local application imports
from app import app, login_manager
from models import User, load_user, create_watering_table
from config import Config
from utils import (
    publish_mqtt_message,
    is_valid_mac,
    is_valid_ip,
    execute_command,
    remote_shutdown_func,
)
from turn_lights import control_wiz_light, get_light_status
from graph import graph_db_data, get_last_reading


# Load user from database
@login_manager.user_loader
def load_user(user_id):
    try:
        conn = sqlite3.connect(Config.USERS_DB_URI)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
    except Exception as e:
        print(f"Error loading user: {e}")

    if user:
        return User(id=user[0], username=user[1], password=user[2])
    return None

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password)

        # Save user to the database
        conn = sqlite3.connect(Config.USERS_DB_URI)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, hashed_password),
        )
        conn.commit()
        conn.close()
        flash("Registration successful. You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(Config.USERS_DB_URI)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            user_obj = User(id=user[0], username=user[1], password=user[2])
            login_user(user_obj)
            flash("Login successful!", "success")
            app.logger.info(f"User '{username}' logged in at {datetime.now()}")
            return redirect(url_for("index"))
        else:
            flash("Invalid username or password. Please try again.", "danger")
            app.logger.warning(f"Failed login attempt for username: '{username}' at {datetime.now()}")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))



@app.route("/temperature")
@login_required
def temperature():
    last_reading = get_last_reading()

    return render_template(
        "temperature.html",
        data_img=graph_db_data("temp"),
        data_img2=graph_db_data("hum"),
        data_img3=graph_db_data("moisture"),
        data_img4=graph_db_data("temp_dht"),
        last_reading=last_reading
    )


@app.route("/send_update", methods=["POST"])
def send_update():
    return publish_mqtt_message(
        "send_update",
        "Update request sent successfully.",
        "Failed to send update request",
    )


@app.route("/lights", methods=["GET", "POST"])
@login_required
def lights():
    light_status = asyncio.run(get_light_status(Config.WIZLIGHT_IP))
    if request.method == "POST":
        light_status = request.form.get("lightStatus")
        if light_status == "ON":
            asyncio.run(control_wiz_light(Config.WIZLIGHT_IP, "ON"))
        elif light_status == "OFF":
            asyncio.run(control_wiz_light(Config.WIZLIGHT_IP, "OFF"))

        else:
            print(f"Invalid lightStatus: {light_status}")

    return render_template("lights.html", light_status=light_status)


@app.route("/take_photo", methods=["POST"])
@login_required
def take_photo():
    # Use the format for filenames that works well with the filesystem and Flask static files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    photo_filename = f"{timestamp}.jpg"
    photo_path = f"/home/javier/SmartHome/static/{photo_filename}"  # Save photo in the static/images folder

    # Take the photo and save it
    os.system(f"rpicam-jpeg -o {photo_path} --rotation 180")

    # Redirect to show_photo with the correct static URL
    return redirect(url_for("show_photo", photo_filename=photo_filename))


@app.route("/show_photo")
@login_required
def show_photo():
    # Get the filename of the photo
    photo_filename = request.args.get("photo_filename")

    # Pass the correct URL for the static photo
    photo_url = url_for("static", filename=f"{photo_filename}")
    return render_template("show_photo.html", photo_url=photo_url)


@app.route("/photo")
@login_required
def photo():
    return render_template("photo.html")



@app.route("/gallery", defaults={"page": 1}, methods=["GET", "POST"])
@app.route("/gallery/page/<int:page>", methods=["GET", "POST"])
@login_required
def gallery(page):
    images = sorted(
        [img for img in os.listdir(Config.IMAGE_DIR) if not img.startswith(".")], reverse=True
    )  # Exclude hidden files
    filtered_images = images

    # Filter images based on date in the filename (assuming format YYYYMMDD_HHMMSS)
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

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
        "gallery.html",
        images=paginated_images,
        page=page,
        has_prev=has_prev,
        has_next=has_next,
    )


@app.route("/slideshow/<filename>")
@login_required
def slideshow(filename):
    # Get the list of images, excluding hidden files
    images = [
        img for img in sorted(os.listdir(Config.IMAGE_DIR)) if not img.startswith(".")
    ]  # Exclude hidden files
    current_index = images.index(filename)

    # Find the previous and next image filenames
    prev_image = images[current_index - 1] if current_index > 0 else images[-1]
    next_image = images[
        (current_index + 1) % len(images)
    ]  # Wrap around to the first image if at the last image

    # Extract the timestamp from the filename (assuming format YYYYMMDD_HHMMSS.jpg)
    timestamp_str = filename.split(".")[0]  # Strip the .jpg
    picture_datetime = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S").strftime(
        "%B %d, %Y at %H:%M:%S"
    )

    # Render the template with image and navigation
    return render_template(
        "slideshow.html",
        image=f"{filename}",
        prev_image=prev_image,
        next_image=next_image,
        picture_datetime=picture_datetime,
    )


@app.route("/remote_wakeup", methods=["GET", "POST"])
@login_required
def wol():
    if request.method == "POST":
        mac_address = request.form.get("macAddress")
        if is_valid_mac(mac_address):
            result = execute_command(f"sudo etherwake -i wlan0 {mac_address}")
        else:
            result = "Error: Invalid MAC address"
    else:  # TODO: Check why is it jumping to this else
        result = None
        if is_valid_mac(Config.REMOTE_PC_MAC):
            result = execute_command(f"sudo etherwake -i wlan0 {Config.REMOTE_PC_MAC}")
        else:
            result = "Error: Invalid MAC address"
    return render_template(
        "remote_power.html", remote_pc_ip=Config.REMOTE_PC_IP, remote_pc_mac=Config.REMOTE_PC_MAC
    )


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
    return render_template(
        "remote_power.html",
        remote_pc_ip=Config.REMOTE_PC_IP,
        remote_pc_mac=Config.REMOTE_PC_MAC,
        result=result,
    )


@app.route("/remote_power")
@login_required
def remote_power():
    return render_template(
        "remote_power.html", remote_pc_ip=Config.REMOTE_PC_IP, remote_pc_mac=Config.REMOTE_PC_MAC
    )

# Route to handle displaying and recording watering
@app.route("/watering", methods=["GET", "POST"])
@login_required
def watering():
    create_watering_table()  # Ensure the table exists

    if request.method == "POST":
        amount_ml = request.form.get("amount_ml") or None
        if amount_ml:
            amount_ml = int(amount_ml)
            if amount_ml < 0:
                flash("Amount must be a positive number.", "danger")
                return redirect(url_for("watering"))
        else:
            amount_ml = None

        try:
            # Connect to the database
            conn = sqlite3.connect(Config.WATERING_DB_URI)
            cursor = conn.cursor()

            time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Insert the new watering record
            cursor.execute(
                "INSERT INTO watering_log (timestamp, amount_ml) VALUES (?, ?)",
                (time_now, amount_ml),
            )
            conn.commit()
            conn.close()

            # Publish the watering event to MQTT
            if amount_ml:
                payload = f"Watered with {amount_ml} ml at {time_now}"
            else:
                payload = f"Watered with no amount at {time_now}"
            
            # Send MQTT message
            try:
                mqtt_client.publish(Config.REMOTE_MQTT_TOPIC_WATERING, payload)
                flash(f"MQTT Correct: {payload}")
            except:
                flash("Error sending MQTT")
            
            # Flash a success message
            flash("Watering record added successfully.", "success")
        except Exception as e:
            print(f"Error: {e}")
            flash(f"Error adding watering record. Please try again. (Error {e})", "danger")

        return redirect(url_for("watering"))

    # Fetch watering logs
    conn = sqlite3.connect(Config.WATERING_DB_URI)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT timestamp, amount_ml, id FROM watering_log ORDER BY timestamp DESC"
    )
    logs = cursor.fetchall()
    conn.close()

    return render_template("watering.html", logs=logs)


@app.route("/delete_watering/<int:log_id>", methods=["POST"])
@login_required
def delete_watering(log_id):
    # Connect to the database
    conn = sqlite3.connect(Config.WATERING_DB_URI)
    cursor = conn.cursor()

    # Delete the record with the given id
    cursor.execute("DELETE FROM watering_log WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()

    # Flash a success message
    flash("Watering record deleted successfully.", "success")

    return redirect(url_for("watering"))


# New route for fan control
@app.route("/fan_control", methods=["GET", "POST"])
@login_required
def fan_control():
    return render_template("fan_control.html")

# Route to handle the "Start Fan" button
@app.route("/start_fan", methods=["POST"])
@login_required
def start_fan():
    try:
        publish_mqtt_message("start_fan", "Fan started successfully.", "Failed to start fan")
    except Exception as e:
        flash(f"Failed to start fan. Error: {e}", "danger")
    return redirect(url_for("fan_control"))

# Route to handle the "Stop Fan" button
@app.route("/stop_fan", methods=["POST"])
@login_required
def stop_fan():
    try:
        publish_mqtt_message("stop_fan", "Fan stopped successfully.", "Failed to stop fan")
    except Exception as e:
        flash(f"Failed to stop fan. Error: {e}", "danger")
    return redirect(url_for("fan_control"))

# Route to handle the "Set Fan Speed" form submission
@app.route("/set_fan_speed", methods=["POST"])
@login_required
def set_fan_speed():
    fan_speed = request.form.get("fan_speed")
    try:
        # Validate that fan_speed is an integer between 0 and 100
        fan_speed_int = int(fan_speed)
        if 0 <= fan_speed_int <= 100:
            message = f"fan_speed_{fan_speed_int}"
            # Publish the MQTT message
            publish_mqtt_message(message, f"Fan speed set to {fan_speed_int}%", "Failed to set fan speed")
        else:
            flash("Invalid fan speed. Please enter a value between 0 and 100.", "danger")
    except ValueError:
        flash("Invalid fan speed. Please enter a numeric value.", "danger")
    except Exception as e:
        flash(f"Failed to set fan speed. Error: {e}", "danger")
    return redirect(url_for("fan_control"))

