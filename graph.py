from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib
from io import BytesIO
import sqlite3
import base64
from config import Config
from datetime import datetime, timedelta
import matplotlib.dates as mdates
from matplotlib.dates import date2num
matplotlib.use('agg')


def graph_db_data(sensor_type):
    # Calculate the datetime 24 hours ago
    datetime_24hrs_ago = datetime.now() - timedelta(hours=24)
    datetime_24hrs_ago_str = datetime_24hrs_ago.strftime('%Y-%m-%d %H:%M:%S')

    # Adjust the query to select records from the last 24 hours
    query = f"""
        SELECT g.date_time_str, g.moisture, g.temperature_ds, g.temperature_dht, g.humidity, g.id
        FROM growdata g
        INNER JOIN (
            SELECT date_time_str, MAX(id) as max_id
            FROM growdata
            WHERE date_time_str >= '{datetime_24hrs_ago_str}'
            GROUP BY date_time_str
        ) AS latest_records ON g.date_time_str = latest_records.date_time_str AND g.id = latest_records.max_id
        ORDER BY g.date_time_str ASC;
    """
    timestamps = []
    temperature_data = []
    humidity_data = []
    moisture_data = []
    temp_dht = []

    try:
        conn = sqlite3.connect(Config.DATA_DB_URI)
        curs = conn.cursor()
        curs.execute(query)
        rows = curs.fetchall()
                # If no records in the last 24 hours, fetch the last 24 records instead.
        if not rows:
            print("No records in the last 24 hours. Fetching last 24 records instead.")
            fallback_query = """
                SELECT g.date_time_str, g.moisture, g.temperature_ds, g.temperature_dht, g.humidity, g.id
                FROM growdata g
                ORDER BY g.date_time_str DESC
                LIMIT 24;
            """
            curs.execute(fallback_query)
            rows = curs.fetchall()
            rows = rows[::-1]  # Reverse to ensure chronological order

        for row in rows:
            # row[0]: date_time_str
            # row[1]: moisture
            # row[2]: temperature_ds
            # row[3]: temperature_dht
            # row[4]: humidity
            # row[5]: id
            timestamp_str = str(row[0])[:19]
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            timestamps.append(timestamp)
            moisture_data.append(round(row[1]))        # moisture
            temperature_data.append(row[2])     # temperature_ds
            temp_dht.append(row[3])             # temperature_dht
            humidity_data.append(row[4])        # humidity

    except Exception as e:
        print("Error occurred while fetching data from the database.")
        print(f"Error: {e}")
        return ""
    finally:
        curs.close()
        conn.close()

    # Convert timestamps to numerical format for Matplotlib
    timestamp_nums = date2num(timestamps)

    # Create the plot
    fig, ax = plt.subplots(figsize=(12, 8), dpi=150)
                           #, constrained_layout=True)

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
        label = "Soil Moisture"
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

    # Plot the data using timestamp_nums
    print(f"Data to plot length: {len(data_to_plot)} - Len of timestamps: {len(timestamp_nums)}")  # Debugging
    ax.plot(timestamp_nums, data_to_plot, label=label, linestyle="-", marker="o", color=color)
    ax.set_title(f"{label} Over Last 24 Hours")
    ax.set_xlabel("Time")
    ax.set_ylabel(y_label)
    ax.fill_between(timestamp_nums, data_to_plot, color=color, alpha=0.1)

    # Adjust y-axis limits to focus on the relevant data range
    # try:
    data_min = min(data_to_plot)
    data_max = max(data_to_plot)
    data_range = data_max - data_min
    # except ValueError:
    #     print("No data to plot.")
    #     return ""
    buffer = data_range * 0.1  # 10% of the data range as buffer

    # Handle case where data_range is zero (all data points are the same)
    if data_range == 0:
        buffer = data_min * 0.1 if data_min != 0 else 1  # Prevent zero buffer
        ax.set_ylim(data_min - buffer, data_max + buffer)
    else:
        ax.set_ylim(data_min - buffer, data_max + buffer)

    # Find the max and min values and their corresponding timestamps
    max_value = data_max
    min_value = data_min
    max_index = data_to_plot.index(max_value)
    min_index = data_to_plot.index(min_value)
    max_time_num = timestamp_nums[max_index]
    min_time_num = timestamp_nums[min_index]

    # Adjust the position of the annotations to avoid overlapping with the title
    ylim = ax.get_ylim()
    y_range = ylim[1] - ylim[0]
    # Position annotations slightly below the max to prevent overlap
    max_y_position = max_value - y_range * 0.05
    min_y_position = min_value + y_range * 0.05

    # # Annotate the max value
    # ax.annotate(f'Max: {max_value}',
    #             xy=(max_time_num, max_value),
    #             xytext=(max_time_num, max_y_position),
    #             arrowprops=dict(facecolor=color, arrowstyle='->'),
    #             ha='center', va='top', color=color, fontsize=10)

    # # Annotate the min value
    # ax.annotate(f'Min: {min_value}',
    #             xy=(min_time_num, min_value),
    #             xytext=(min_time_num, min_y_position),
    #             arrowprops=dict(facecolor=color, arrowstyle='->'),
    #             ha='center', va='bottom', color=color, fontsize=10)
    
        # Annotate the max value
    ax.annotate(f'Max: {max_value}',
                xy=(max_time_num, max_value),
                xytext=(max_time_num, max_value - y_range * 0.05),  # Position slightly below
                arrowprops=dict(facecolor=color, arrowstyle='->'),
                ha='center', va='top', color=color, fontsize=10)

    # Annotate the min value
    ax.annotate(f'Min: {min_value}',
                xy=(min_time_num, min_value),
                xytext=(min_time_num, min_value + y_range * 0.05),  # Position slightly above
                arrowprops=dict(facecolor=color, arrowstyle='->'),
                ha='center', va='bottom', color=color, fontsize=10)


    # Draw horizontal and vertical lines for max and min values
    ax.axhline(y=max_value, color=color, linestyle='--', alpha=0.5)
    ax.axvline(x=max_time_num, color=color, linestyle='--', alpha=0.5)
    ax.axhline(y=min_value, color=color, linestyle='--', alpha=0.5)
    ax.axvline(x=min_time_num, color=color, linestyle='--', alpha=0.5)

    # Set x-axis ticks to match the data points
    ax.set_xticks(timestamp_nums)
    # Format the x-axis labels to show only time to save space
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=60))
    

    # Rotate x-axis labels and adjust layout
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
    #plt.subplots_adjust(bottom=0.3, top=0.85)  # Adjust top to give space for the title

    # Enable grid for better readability
    ax.grid(True, which='both', linestyle='--', linewidth=0.5, alpha=0.7)


# Test
    #fig.tight_layout()


    # Convert the plot to a base64-encoded string
    buf = BytesIO()
    fig.savefig(buf, format="png")  # Removed bbox_inches='tight'
    data = base64.b64encode(buf.getvalue()).decode("ascii")
    plt.close(fig)  # Close the figure to free memory
    return f"<img class='img-fluid graph-image' src='data:image/png;base64,{data}'/>"


def get_last_reading():
    query = "SELECT * FROM growdata ORDER BY date_time_str DESC LIMIT 1;"  # Get the latest record
    try:
        conn = sqlite3.connect(Config.DATA_DB_URI)
        curs = conn.cursor()
        curs.execute(query)
        row = curs.fetchone()  # Get the latest row
        if row:
            timestamp_str = str(row[0])[:19]  # Get the timestamp, format it
            temperature_ds = row[2]  # Temperature from DS sensor
            temp_dht = row[3]  # Temperature from DHT sensor
            humidity = row[4]  # Humidity from DHT sensor
            moisture = round(row[1])  # Moisture level

            # Format the string for the latest readings
            last_reading = f"Last reading: {timestamp_str} - Temperature DHT: {temp_dht}°C - Humidity: {humidity}% - Temperature Soil: {temperature_ds}°C - Moisture: {moisture}%"
            return last_reading
        else:
            return "No readings available."
    except Exception as e:
        print(f"Error fetching last reading: {e}")
        return "Error fetching data"
    finally:
        curs.close()
        conn.close()
