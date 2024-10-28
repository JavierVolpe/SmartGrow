import sqlite3
from datetime import datetime
from time import sleep
import paho.mqtt.subscribe as subscribe
import paho.mqtt.publish as publish


mqtt_local_broker   = "localhost"
mqtt_local_topic    = "javier/growdata"
db_path             = "db/data.db"


def create_table():
    conn = sqlite3.connect(db_path)
    curs = conn.cursor()

    curs.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='growdata' LIMIT 1;")
    if curs.fetchone():
        print("Table already exists. Starting program...")
    else:
        query = """CREATE TABLE growdata (date_time_str TEXT, moisture REAL, temperature_ds REAL, temperature_dht REAL, humidity REAL, battery REAL)"""
        try:
            curs.execute(query)
            conn.commit()
            print("Table created successfully")
        except Exception as e:
            print("Error:", e)
            print("Failed to connect to the database")
            conn.rollback()
        finally:
            curs.close()

def log_grow_data(client, userdata, message):
    query = """INSERT INTO growdata (date_time_str, moisture, temperature_ds, temperature_dht, humidity) VALUES (?,?,?,?,?)"""
    msg_str = message.payload.decode("utf-8")
    date_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    moisture, temperature_ds, temperature_dht, humidity = msg_str.split("|") 
    #temperature_dht = temperature_dht.split(".")[0] # Remove the decimal part of the temperature value
    #humidity = humidity.split(".")[0] # Remove the decimal part of the humidity value
    temperature_dht = float(temperature_dht)
    temperature_ds = float(temperature_ds)
    humidity = float(humidity)
    moisture = float(moisture)
    data = (date_time_str, moisture, temperature_ds, temperature_dht, humidity)


    """     if data[5] == True or data[5] == "True" or data[5] == "1": 
        print("Der er ild !!!! Dataen sendes til Azure med det samme")
        send_string = f"{data[0]}|{data[1]}|{data[2]}|{data[3]}|{data[4]}|{data[5]}" 
        try:
            # publish.single(mqtt_remote_topic, str(send_string), hostname=mqtt_remote_broker) 
            print(f"Data NOT sent to Azure: {send_string}")
            ..
        except Exception as e:
            print("Error:", e)
            print("Failed to send data to Azure") """
    print("date_time_str, moisture, temperature_ds, temperature_dht, humidity")
    print(f"Data to be inserted: {data}")
    print()

    try:
        conn = sqlite3.connect(db_path)
        curs = conn.cursor()
        curs.execute(query, data)
        conn.commit() 
    except Exception as e:
        print("Error:", e)
        print("Failed to connect to the database")
        conn.rollback()
    finally:
        curs.close()
    sleep(0.5)

def start_logging():
    """
    This function starts the logging process.
    """
    try:
        create_table() 
        print("Program started")
        subscribe.callback(log_grow_data, mqtt_local_topic, hostname=mqtt_local_broker) 
        print("Program stopped")
    except Exception as e:
        print("Error:", e)
    except KeyboardInterrupt:
        print("Program stopped by the user")

start_logging()
