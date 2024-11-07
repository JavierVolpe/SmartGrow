from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from io import BytesIO
import sqlite3
import base64

def graph_db_data(sensor_type="temp", number_of_rows=24):
    # Fetch the last 24 records from the database
    query = "SELECT * FROM growdata ORDER BY date_time_str DESC LIMIT ?;"
    timestamps, temperature_data, humidity_data, moisture_data, temp_dht = [], [], [], [], []
    
    try:
        conn = sqlite3.connect('db/data.db')
        curs = conn.cursor()
        curs.execute(query, (number_of_rows,))
        rows = curs.fetchall()[::-1]  # Reverse to get chronological order
        for row in rows:
            timestamps.append(str(row[0])[:19])  # Remove milliseconds
            temperature_data.append(row[2])  # temperature_ds
            temp_dht.append(row[3])  # temperature_dht
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
    ax.plot(timestamps, data_to_plot, label=label, linestyle="-", marker="o", color=color)
    ax.set_title(f"{label} Over Last {number_of_rows} Records")
    ax.set_ylabel(y_label)
    ax.fill_between(timestamps, data_to_plot, color=color, alpha=0.1)

    # Highlight the highest and lowest points
    max_value = max(data_to_plot)
    min_value = min(data_to_plot)
    max_index = data_to_plot.index(max_value)
    min_index = data_to_plot.index(min_value)

    # Set the y-axis limits to add space for annotations
    ax.set_ylim(min_value - 1, max_value + 1)  # Add some padding around the data

    # Conditionally annotate max and min values if they are different
    if max_value != min_value:
        ax.annotate(f'Max: {max_value}', xy=(timestamps[max_index], max_value), 
                    xytext=(timestamps[max_index], max_value + 0.5),
                    arrowprops=dict(facecolor=color, arrowstyle="->"),
                    ha="center", color=color, fontsize=10)

        ax.annotate(f'Min: {min_value}', xy=(timestamps[min_index], min_value), 
                    xytext=(timestamps[min_index], min_value - 0.5),
                    arrowprops=dict(facecolor=color, arrowstyle="->"),
                    ha="center", color=color, fontsize=10)

    # Format the x-axis
    ax.set_xlabel("Time")
    ax.tick_params(axis="x", rotation=45)
    ax.invert_xaxis()  # Show the latest data on the right

    plt.subplots_adjust(top=0.9, bottom=0.2, left=0.1, right=0.9, hspace=0.4, wspace=0.4)
    fig.tight_layout()  # Ensure no overlap in elements

    # Convert the plot to a base64-encoded string
    buf = BytesIO()
    fig.savefig(buf, format="png")
    data = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"<img class='img-fluid' src='data:image/png;base64,{data}'/>"
