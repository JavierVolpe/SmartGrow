# Standard library imports
import asyncio
import os
import sqlite3
from datetime import datetime

# Third-party imports
import requests
from flask import (render_template, request, redirect, url_for, flash, session, jsonify)
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

# Local application imports
from app import app, login_manager
from config import Config
from models import User, load_user, create_watering_table
from device_control import (
    mqtt_client,             # The global ShellyPlugMQTTClient instance
    is_valid_ip,
    is_valid_mac,
    remote_shutdown_func,
    execute_command,
    get_light_status, 
    set_light_state, 
    turn_off_light,
    get_light_status_sync, 
    set_light_state_sync, 
    turn_off_light_sync
)
from matplotlib.figure import Figure
from io import BytesIO
import base64
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

from utils import execute_command, is_valid_ip, is_valid_mac, publish_mqtt_message, remote_shutdown_func
from cron_manager import CronManager
from wiz_manager import update_light, turn_off_light, get_light_status, WIZ_LIGHTS

# Set up the user loader from models (avoid redefinition)
login_manager.user_loader(load_user)

cm = CronManager()

# --------------------------------------------------
# Main Site Routes
# --------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
@login_required # Ensure only logged-in users can register
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password)

        # Save user to the database
        conn = sqlite3.connect(Config.USERS_DB_URI)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
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


# --------------------------------------------------
# Temperature, Photo, and Gallery Routes
# --------------------------------------------------

@app.route("/temperature", methods=["GET", "POST"])
@login_required
def temperature():
    if request.method == "POST":
        return publish_mqtt_message(
            "send_update",
            "Update request sent successfully.",
            "Failed to send update request",
        )

    end_time = datetime.now()
    start_time = end_time - timedelta(days=1)

    start_date = request.args.get("start_date") or start_time.strftime("%Y-%m-%d")
    end_date = request.args.get("end_date") or end_time.strftime("%Y-%m-%d")

    query = """
        SELECT date_time_str, temperature_dht, temperature_ds, humidity
        FROM growdata
        WHERE date_time_str BETWEEN ? AND ?
        ORDER BY date_time_str DESC
    """
    params = [f"{start_date} 00:00:00", f"{end_date} 23:59:59"]

    conn = sqlite3.connect(Config.DATA_DB_URI)
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    def analyze_with_time(data, index):
        values = [(row[0], row[index]) for row in rows if row[index] is not None]
        if not values:
            return {"max": None, "max_time": None, "min": None, "min_time": None, "avg": None}
        max_val, max_time = max((val, ts) for ts, val in values)
        min_val, min_time = min((val, ts) for ts, val in values)
        avg_val = round(sum(val for _, val in values) / len(values), 2)
        return {
            "max": max_val, "max_time": max_time,
            "min": min_val, "min_time": min_time,
            "avg": avg_val
        }

    trends = {
        "dht": analyze_with_time(rows, 1),
        "ds": analyze_with_time(rows, 2),
        "hum": analyze_with_time(rows, 3),
    }

    # Generate sparklines
    def create_sparkline(index, label):
        times = [datetime.strptime(r[0], "%Y-%m-%d %H:%M:%S") for r in rows if r[index] is not None]
        values = [r[index] for r in rows if r[index] is not None]
        fig = Figure(figsize=(4, 2), dpi=100)
        ax = fig.add_subplot(1, 1, 1)
        ax.plot(times, values, linewidth=1.5)
        ax.set_title(label, fontsize=8, color='white')
        ax.set_facecolor("#2a2a2a")
        fig.patch.set_facecolor("#1f1f1f")
        ax.tick_params(axis='x', labelsize=6, colors='white')
        ax.tick_params(axis='y', labelsize=6, colors='white')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.grid(True, linestyle="--", alpha=0.3)
        buf = BytesIO()
        fig.tight_layout()
        fig.savefig(buf, format="png", transparent=True)
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    graphs = {
        "dht": create_sparkline(1, "Ambient Temp"),
        "ds": create_sparkline(2, "Soil Temp"),
        "hum": create_sparkline(3, "Humidity"),
    }

    return render_template(
        "temperature_log.html",
        rows=rows,
        start_date=start_date,
        end_date=end_date,
        trends=trends,
        graphs=graphs
    )

@app.route("/send_update", methods=["POST"])
@login_required
def send_update():
    return publish_mqtt_message(
        "send_update",
        "Update request sent successfully.",
        "Failed to send update request",
    )

@app.route("/take_photo", methods=["POST"])
@login_required
def take_photo():
    try:
        # Trigger photo capture on Raspberry Pi
        response = requests.post(Config.PI_CAPTURE_URL)
        response.raise_for_status()
        data = response.json()
        photo_filename = data.get("filename")
        if not photo_filename:
            flash("No photo filename returned by the camera API.")
            return redirect(url_for("photo"))
        
        # Download the photo from Pi's static endpoint
        photo_url = f"{Config.PI_STATIC_URL}/{photo_filename}"
        r = requests.get(photo_url)
        r.raise_for_status()

        # Save the photo locally for gallery/slideshow
        local_photo_path = os.path.join(Config.LOCAL_STATIC_DIR, photo_filename)
        with open(local_photo_path, "wb") as f:
            f.write(r.content)
        
        return redirect(url_for("show_photo", photo_filename=photo_filename))
    except requests.RequestException as e:
        flash(f"Error capturing photo: {e}")
        return redirect(url_for("photo"))


@app.route("/show_photo")
@login_required
def show_photo():
    photo_filename = request.args.get("photo_filename")
    photo_url = url_for("static", filename=photo_filename)
    return render_template("show_photo.html", photo_url=photo_url)


@app.route("/photo")
@login_required
def photo():
    return render_template("photo.html")


@app.route("/gallery", defaults={"page": 1}, methods=["GET", "POST"])
@app.route("/gallery/page/<int:page>", methods=["GET", "POST"])
@login_required
def gallery(page):
    images = sorted([img for img in os.listdir(Config.LOCAL_STATIC_DIR) if not img.startswith(".")], reverse=True)
    filtered_images = images

    # Optional date filtering by filename (YYYYMMDD)
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    if start_date and end_date:
        filtered_images = [img for img in images if start_date <= img[:8] <= end_date]

    images_per_page = 12
    total_images = len(filtered_images)
    start_index = (page - 1) * images_per_page
    end_index = start_index + images_per_page
    paginated_images = filtered_images[start_index:end_index]
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
    images = [img for img in sorted(os.listdir(Config.LOCAL_STATIC_DIR)) if not img.startswith(".")]
    current_index = images.index(filename)
    prev_image = images[current_index - 1] if current_index > 0 else images[-1]
    next_image = images[(current_index + 1) % len(images)]
    timestamp_str = filename.split(".")[0]
    picture_datetime = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S").strftime("%B %d, %Y at %H:%M:%S")
    return render_template(
        "slideshow.html",
        image=filename,
        prev_image=prev_image,
        next_image=next_image,
        picture_datetime=picture_datetime,
    )


# --------------------------------------------------
# Remote Control and Watering Routes
# --------------------------------------------------

@app.route("/remote_wakeup", methods=["GET", "POST"])
@login_required
def wol():
    result = None
    if request.method == "POST":
        mac_address = request.form.get("macAddress")
        if is_valid_mac(mac_address):
            try:
                address = "http://" + Config.PI_IP + ":5000/api/wol"
                response = requests.post(address, data={"macAddress": mac_address}, timeout=5)
                result = f"✅ Raspberry Pi says: {response.text}"
            except requests.RequestException as e:
                result = f"❌ Could not reach Raspberry Pi: {e}"
        else:
            result = "❌ Error: Invalid MAC address"

    return render_template(
        "remote_power.html",
        remote_pc_ip=Config.REMOTE_PC_IP,
        remote_pc_mac=Config.REMOTE_PC_MAC,
        result=result
    )




@app.route("/remote_shutdown", methods=["GET", "POST"])
@login_required
def remote_shutdown():
    if request.method == "POST":
        ip_address = request.form.get("ipAddress")
        if is_valid_ip(ip_address):
            result = f"Result: Remote shutdown command sent to {ip_address}" if remote_shutdown_func(ip_address) else f"Error: Remote shutdown command failed for {ip_address}"
        else:
            result = "Error: Invalid IP address"
    else:
        result = ""
    return render_template("remote_power.html", remote_pc_ip=Config.REMOTE_PC_IP, remote_pc_mac=Config.REMOTE_PC_MAC, result=result)


@app.route("/remote_power")
@login_required
def remote_power():
    return render_template("remote_power.html", remote_pc_ip=Config.REMOTE_PC_IP, remote_pc_mac=Config.REMOTE_PC_MAC)


@app.route("/watering", methods=["GET", "POST"])
@login_required
def watering():
    create_watering_table()  # Ensure the table exists
    if request.method == "POST":
        amount_ml = request.form.get("amount_ml")
        if amount_ml:
            amount_ml = int(amount_ml)
            if amount_ml < 0:
                flash("Amount must be a positive number.", "danger")
                return redirect(url_for("watering"))
        else:
            amount_ml = None
        try:
            conn = sqlite3.connect(Config.WATERING_DB_URI)
            cursor = conn.cursor()
            time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO watering_log (timestamp, amount_ml) VALUES (?, ?)", (time_now, amount_ml))
            conn.commit()
            conn.close()
            flash("Watering record added successfully.", "success")
        except Exception as e:
            flash(f"Error adding watering record. Please try again. (Error {e})", "danger")
        return redirect(url_for("watering"))

    conn = sqlite3.connect(Config.WATERING_DB_URI)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, amount_ml, id FROM watering_log ORDER BY timestamp DESC")
    logs = cursor.fetchall()
    conn.close()
    return render_template("watering.html", logs=logs)


@app.route("/delete_watering/<int:log_id>", methods=["POST"])
@login_required
def delete_watering(log_id):
    conn = sqlite3.connect(Config.WATERING_DB_URI)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM watering_log WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()
    flash("Watering record deleted successfully.", "success")
    return redirect(url_for("watering"))


# --------------------------------------------------
# Fan, Pump, and Smart Plug Control Routes
# --------------------------------------------------

@app.route("/fan_control", methods=["GET", "POST"])
@login_required
def fan_control():
    return render_template("fan_control.html")


@app.route("/start_fan", methods=["POST"])
@login_required
def start_fan():
    try:
        publish_mqtt_message("start_fan", "Fan started successfully.", "Failed to start fan")
    except Exception as e:
        flash(f"Failed to start fan. Error: {e}", "danger")
    return redirect(url_for("fan_control"))


@app.route("/stop_fan", methods=["POST"])
@login_required
def stop_fan():
    try:
        publish_mqtt_message("stop_fan", "Fan stopped successfully.", "Failed to stop fan")
    except Exception as e:
        flash(f"Failed to stop fan. Error: {e}", "danger")
    return redirect(url_for("fan_control"))


@app.route("/start_bottom_fan", methods=["POST"])
@login_required
def start_bottom_fan():
    try:
        publish_mqtt_message("start_bottom_fan", "Extra Fan started successfully.", "Failed to start fan")
    except Exception as e:
        flash(f"Failed to start fan. Error: {e}", "danger")
    return redirect(url_for("fan_control"))


@app.route("/stop_bottom_fan", methods=["POST"])
@login_required
def stop_bottom_fan():
    try:
        publish_mqtt_message("stop_bottom_fan", "Extra Fan stopped successfully.", "Failed to stop fan")
    except Exception as e:
        flash(f"Failed to stop fan. Error: {e}", "danger")
    return redirect(url_for("fan_control"))


@app.route("/start_pump", methods=["POST"])
@login_required
def start_pump():
    try:
        publish_mqtt_message("start_pump", "Pump started successfully.", "Failed to start Pump")
    except Exception as e:
        flash(f"Failed to start Pump. Error: {e}", "danger")
    return redirect(url_for("fan_control"))


@app.route("/stop_pump", methods=["POST"])
@login_required
def stop_pump():
    try:
        publish_mqtt_message("stop_pump", "Pump stopped successfully.", "Failed to stop Pump")
    except Exception as e:
        flash(f"Failed to stop Pump. Error: {e}", "danger")
    return redirect(url_for("fan_control"))


@app.route("/set_fan_speed", methods=["POST"])
@login_required
def set_fan_speed():
    fan_speed = request.form.get("fan_speed")
    try:
        fan_speed_int = int(fan_speed)
        if 0 <= fan_speed_int <= 100:
            message = f"fan_speed_{fan_speed_int}"
            publish_mqtt_message(message, f"Fan speed set to {fan_speed_int}%", "Failed to set fan speed")
        else:
            flash("Invalid fan speed. Please enter a value between 0 and 100.", "danger")
    except ValueError:
        flash("Invalid fan speed. Please enter a numeric value.", "danger")
    except Exception as e:
        flash(f"Failed to set fan speed. Error: {e}", "danger")
    return redirect(url_for("fan_control"))


@app.route("/smart_plug", methods=["GET", "POST"])
@login_required
def smart_plug():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "turn_on":
            try:
                mqtt_client.set_plug_state(True)
                flash("Plug turned ON.", "success")
            except Exception as e:
                flash(f"Failed to turn ON the plug. Error: {e}", "danger")
        elif action == "turn_off":
            try:
                mqtt_client.set_plug_state(False)
                flash("Plug turned OFF.", "success")
            except Exception as e:
                flash(f"Failed to turn OFF the plug. Error: {e}", "danger")
        else:
            flash("Invalid action.", "danger")
        return redirect(url_for("smart_plug"))
    else:
        status = mqtt_client.get_plug_status()
        schedule_info = mqtt_client.get_next_status_change()
        return render_template("smart_plug.html", status=status, schedule_info=schedule_info)


@app.route("/reset_esp", methods=["POST"])
@login_required
def reset_esp():
    try:
        publish_mqtt_message("reset", "ESP32 reset sent", "Failed to send reset")
    except Exception as e:
        flash(f"Failed to send reset Error: {e}", "danger")
    return redirect(url_for("fan_control"))


# --------------------------------------------------
# Calculator and Dashboard Routes
# --------------------------------------------------

@app.route('/calculate', methods=['GET', 'POST'])
def calculate():
    date_input = request.form.get('start_date', Config.PLANTATION_DATE)
    try:
        start_date = datetime.strptime(date_input, '%Y-%m-%d')
        today = datetime.today()
        delta = today - start_date
        result = {
            'weeks': delta.days // 7,
            'days': delta.days % 7,
            'total_days': delta.days,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'today': today.strftime('%Y-%m-%d')
        }
    except ValueError:
        result = {'error': 'Invalid date format. Please use YYYY-MM-DD.'}
    return render_template('calculate.html', result=result, date_input=date_input)


@app.route('/dashboard')
@login_required
def dashboard():
    sensor_data = get_last_reading()
    # Using asyncio to get light status from wiz_manager
    light_status = asyncio.run(get_light_status(Config.WIZLIGHT_IP))
    conn = sqlite3.connect(Config.WATERING_DB_URI)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, amount_ml FROM watering_log ORDER BY timestamp DESC LIMIT 1")
    last_watering = cursor.fetchone()
    conn.close()
    smart_plug_status = mqtt_client.get_plug_status()
    return render_template('dashboard.html',
                           sensor_data=sensor_data,
                           light_status=light_status,
                           last_watering=last_watering,
                           smart_plug_status=smart_plug_status)


# --------------------------------------------------
# Extra Fan Control (Dry House)
# --------------------------------------------------

@app.route("/start_dry_fan", methods=["POST"])
@login_required
def start_dry_fan():
    try:
        publish_mqtt_message("fan_speed_60", "Dry Fan started successfully at 60%.", "Failed to start Dry Fan", "dry/control")
    except Exception as e:
        flash(f"Failed to start Dry Fan. Error: {e}", "danger")
    return redirect(url_for("fan_control"))


@app.route("/stop_dry_fan", methods=["POST"])
@login_required
def stop_dry_fan():
    try:
        publish_mqtt_message("stop_fan", "Dry Fan stopped successfully.", "Failed to stop Dry Fan", "dry/control")
    except Exception as e:
        flash(f"Failed to stop Dry Fan. Error: {e}", "danger")
    return redirect(url_for("fan_control"))


@app.route("/set_dry_fan_speed", methods=["POST"])
@login_required
def set_dry_fan_speed():
    dry_fan_speed = request.form.get("dry_fan_speed")
    try:
        dry_fan_speed_int = int(dry_fan_speed)
        if 0 <= dry_fan_speed_int <= 100:
            message = f"fan_speed_{dry_fan_speed_int}"
            publish_mqtt_message(message, f"Dry Fan speed set to {dry_fan_speed_int}%", "Failed to set Dry Fan speed", "dry/control")
        else:
            flash("Invalid dry fan speed. Please enter a value between 0 and 100.", "danger")
    except ValueError:
        flash("Invalid dry fan speed. Please enter a numeric value.", "danger")
    except Exception as e:
        flash(f"Failed to set Dry Fan speed. Error: {e}", "danger")
    return redirect(url_for("fan_control"))


# --------------------------------------------------
# WiZ Light Control Routes (API)
# --------------------------------------------------

@app.route("/wiz_control")
@login_required
def wiz_control():
    return render_template("wiz_control.html", wiz_lights=WIZ_LIGHTS, active_menu="wiz_control")

# Route to set light state (brightness and color)
@app.route("/api/set_light", methods=["POST"])
@login_required
def set_light_api():
    data = request.get_json()
    lamp_name = data.get("lamp_name")
    ip_address = WIZ_LIGHTS.get(lamp_name)
    brightness = data.get("brightness", 255)
    r = data.get("r", 255)
    g = data.get("g", 255)
    b = data.get("b", 255)

    try:
        result = set_light_state_sync(ip_address, brightness, r, g, b)
        if result:
            return jsonify({"status": "success"})
        return jsonify({"error": "Failed to set light state"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# Route to turn off light
@app.route("/api/turn_off_light", methods=["POST"])
@login_required
def turn_off_light_api():
    data = request.get_json()
    lamp_name = data.get("lamp_name")
    ip_address = WIZ_LIGHTS.get(lamp_name)

    try:
        result = turn_off_light_sync(ip_address)
        if result:
            return jsonify({"status": "success"})
        return jsonify({"error": "Failed to turn off light"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route("/api/get_light_status", methods=["POST"])
@login_required
def get_light_status_api():
    data = request.get_json()
    lamp_name = data.get("lamp_name")
    ip_address = WIZ_LIGHTS.get(lamp_name)

    try:
        status = asyncio.run(get_light_status(ip_address))
        if "error" in status:
            return jsonify({"error": status["error"]}), 500
        return jsonify({"status": "success", "data": status})
    except Exception as e:
        return jsonify({"error": str(e)}), 500





# --------------------------------------------------
# Cron List
# --------------------------------------------------

@app.route('/cron_list')
@login_required
def cron_list():


    """
    The index page displays the current cron jobs with options to edit or delete.
    """
    jobs = cm.get_jobs()
    return render_template('cron_list.html', cron_jobs=jobs, active_menu='cron')


@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_task():
    """
    A page to add a new cron job interactively.
    Allows selection between a standard cron job or a special cron job (e.g. @reboot).
    """
    if request.method == 'POST':
        job_type = request.form.get('job_type', 'standard')
        if job_type == 'standard':
            minute = request.form.get('minute', '*').strip() or '*'
            hour = request.form.get('hour', '*').strip() or '*'
            day_of_month = request.form.get('day_of_month', '*').strip() or '*'
            month = request.form.get('month', '*').strip() or '*'
            day_of_week = request.form.get('day_of_week', '*').strip() or '*'
            command = request.form.get('command', '').strip()
            if not command:
                flash('Command cannot be empty for standard job.', 'danger')
                return redirect(url_for('add_task'))
            job_line = f"{minute} {hour} {day_of_month} {month} {day_of_week} {command}"
        else:  # special job
            special_schedule = request.form.get('special_schedule', '').strip()
            command_special = request.form.get('command_special', '').strip()
            if not special_schedule:
                flash('Special schedule cannot be empty.', 'danger')
                return redirect(url_for('add_task'))
            if not command_special:
                flash('Command cannot be empty for special job.', 'danger')
                return redirect(url_for('add_task'))
            job_line = f"{special_schedule} {command_special}"
        try:
            cm.add_job(job_line)
            flash('Cron job added successfully.', 'success')
            return redirect(url_for('cron_list'))
        except Exception as e:
            flash(f'Error adding job: {e}', 'danger')
            return redirect(url_for('add_task'))
    return render_template('add_task.html', active_menu='cron')

@app.route('/edit/<int:index>', methods=['GET', 'POST'])
@login_required
def edit_task(index):
    """
    A page to edit an existing cron job.
    If the job uses a special schedule (e.g. @reboot), a single input field is provided.
    Otherwise, the standard interactive fields are shown.
    """
    jobs = cm.get_jobs()
    if index < 0 or index >= len(jobs):
        flash('Invalid job index.', 'danger')
        return redirect(url_for('cron_list'))

    current_job = jobs[index]
    # Determine if the job is "special" (e.g. starts with '@' or not in standard format)
    parts = current_job.split()
    is_special = current_job.startswith('@') or len(parts) < 6

    if request.method == 'POST':
        if is_special:
            job_line = request.form.get('job_line', '').strip()
            if not job_line:
                flash('Cron job line cannot be empty.', 'danger')
                return redirect(url_for('edit_task', index=index))
        else:
            minute = request.form.get('minute', '').strip()
            hour = request.form.get('hour', '').strip()
            day_of_month = request.form.get('day_of_month', '').strip()
            month = request.form.get('month', '').strip()
            day_of_week = request.form.get('day_of_week', '').strip()
            command = request.form.get('command', '').strip()
            if not command:
                flash('Command cannot be empty.', 'danger')
                return redirect(url_for('edit_task', index=index))
            job_line = f"{minute} {hour} {day_of_month} {month} {day_of_week} {command}"
        try:
            cm.update_job_by_index(index, job_line)
            flash('Cron job updated successfully.', 'success')
            return redirect(url_for('cron_list'))
        except Exception as e:
            flash(f'Error updating job: {e}', 'danger')
            return redirect(url_for('edit_task', index=index))

    if is_special:
        # For special jobs, pass the whole line
        return render_template('edit_task.html',
                               index=index,
                               is_special=True,
                               job_line=current_job,
                               active_menu='cron')
    else:
        # Standard job: split into 5 cron fields and the command
        cron_parts = parts[:5]
        command_part = " ".join(parts[5:])
        return render_template('edit_task.html',
                               index=index,
                               is_special=False,
                               minute=cron_parts[0],
                               hour=cron_parts[1],
                               day_of_month=cron_parts[2],
                               month=cron_parts[3],
                               day_of_week=cron_parts[4],
                               command=command_part,
                               active_menu='cron')

@app.route('/delete/<int:index>', methods=['POST'])
@login_required
def delete_task(index):
    """
    Delete a cron job by its index.
    """
    try:
        cm.remove_job_by_index(index)
        flash('Cron job deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting job: {e}', 'danger')
    return redirect(url_for('cron_list'))


if __name__ == '__main__':
    app.run(debug=True)
