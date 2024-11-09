from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib
from io import BytesIO
import sqlite3
import base64
from config import Config
from datetime import datetime
import matplotlib.dates as mdates
matplotlib.use('agg')


def graph_db_data(sensor_type, number_of_rows=48):
    query = "SELECT DISTINCT date_time_str, * FROM growdata ORDER BY date_time_str DESC LIMIT ?;"
    timestamps, temperature_data, humidity_data, moisture_data, temp_dht = [], [], [], [], []

    try:
        conn = sqlite3.connect(Config.DATA_DB_URI)
        curs = conn.cursor()
        curs.execute(query, (number_of_rows,))
        rows = curs.fetchall()

        for row in rows:
            # Use full timestamp including seconds
            timestamp_str = str(row[0])[:19]
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            timestamps.append(timestamp)
            temperature_data.append(row[2])  # temperature_ds
            temp_dht.append(row[3])          # temperature_dht
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
    fig, ax = plt.subplots(figsize=(12, 8))  # Increased figure size
    plt.style.use('dark_background')

    # Determine the data to plot based on the sensor type
    if sensor_type == "temp":
        data_to_plot = temperature_data
        label = "Temperature"
        color = "r"
        y_label = "Temperature (°C)"
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

    # Plot the data
    print(f"Data to plot length: {len(data_to_plot)} - Len of timestamps {len(timestamps)}")  # Debugging
    ax.plot(timestamps, data_to_plot, label=label, linestyle="-", marker="o", color=color)
    ax.set_title(f"{label} Over Last {number_of_rows} Records")
    ax.set_ylabel(y_label)
    ax.fill_between(timestamps, data_to_plot, color=color, alpha=0.1)

    # Format the x-axis to show time with the correct frequency
    ax.set_xlabel("Time")
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))  # Show time in hours and minutes
    ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=60))  # Set locator for every 30 minutes
    fig.autofmt_xdate()  # Automatically format x-axis labels to prevent overlap

    plt.subplots_adjust(top=0.9, bottom=0.2, left=0.1, right=0.9)

    # Convert the plot to a base64-encoded string
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight')
    data = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"<img class='img-fluid' src='data:image/png;base64,{data}'/>"
