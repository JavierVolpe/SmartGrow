import sqlite3
from datetime import datetime
from time import sleep
import paho.mqtt.subscribe as subscribe
import paho.mqtt.publish as publish
from config import Config

mqtt_local_broker   = Config.MQTT_BROKER_IP
mqtt_local_topic    = Config.MQTT_SUB_TOPIC
db_path             = Config.DATA_DB_URI

 
def create_table():
    conn = sqlite3.connect(db_path)
    curs = conn.cursor()

    curs.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='growdata' LIMIT 1;")
    if curs.fetchone():
        print("Table already exists. Starting program...")
    else:
        query = """CREATE TABLE growdata (date_time_str TEXT, moisture REAL, temperature_ds REAL, temperature_dht REAL, humidity REAL, id INTEGER PRIMARY KEY AUTOINCREMENT)"""
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
    #print("Message received:", msg_str)
    date_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if len(msg_str.split("|")) != 4:
        print(f"Invalid message format received: {msg_str}")
        return
    else:
        moisture, temperature_ds, temperature_dht, humidity = msg_str.split("|") 
        #temperature_dht = temperature_dht.split(".")[0] # Remove the decimal part of the temperature value
        #humidity = humidity.split(".")[0] # Remove the decimal part of the humidity value
        temperature_dht = float(temperature_dht)
        temperature_ds = float(temperature_ds)
        humidity = float(humidity)
        #moisture = float(moisture)
        moisture = moisture.split(".")[0] # Remove the decimal part of the moisture value
        data = (date_time_str, moisture, temperature_ds, temperature_dht, humidity)

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
