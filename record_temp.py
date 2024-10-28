# This script reads the temperature and humidity from a DHT11 sensor and logs the data to a SQLite database
# It should be run as: nohup python record_temp.py > log_temp.txt 2>&1 &

import sqlite3
from datetime import datetime
from random import randint
from time import sleep 
import board
import adafruit_dht
import time


db_path = 'db/sensor_data.db'
def read_dht11(pin):
    dht_device = adafruit_dht.DHT11(pin)
    while True:
        try:
            temperature_c = dht_device.temperature
            humidity = dht_device.humidity
            dht_device.exit() # IMPORTANT: This is needed to release the pin so it can be used by other devices
            return humidity, temperature_c
        except RuntimeError as e:
            print("Failed to retrieve data from DHT11 sensor:", e)
            print("Retrying in 2 seconds...")
            time.sleep(2)
            continue


def create_table():
    query = """ CREATE TABLE IF NOT EXISTS stue (datetime TEXT, temperature REAL, humidity REAL)"""
    try:
        conn = sqlite3.connect(db_path)
        curs = conn.cursor()
        
        # Check if the table already exists
        curs.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stue'")
        table_exists = curs.fetchone()
        if table_exists:
            print('Table already exists')
        else:
            curs.execute(query)
            conn.commit()
            print('Table created successfully')
    except Exception as e:
        print('Error:', e)
        print('Failed to connect to the database')
        conn.rollback()
    finally:
        curs.close()


def log_stue_data():
    while True: 
                
        query = """INSERT INTO stue (datetime, temperature, humidity) VALUES (?, ?, ?)"""
        time = datetime.now()
        time = time.strftime('%Y-%m-%d %H:%M:%S')
        try:
            humidity, temperature = read_dht11(board.D26)
        except Exception as e:
            print('Error:', e)
            print('Failed to read data from DHT11 sensor')
            continue
        data = (time, temperature, humidity)


        # Connect to the database
        try:
            conn = sqlite3.connect(db_path)
            curs = conn.cursor()
            curs.execute(query, data)
            conn.commit()
            print(f"Data inserted successfully: {data}")
        except Exception as e:
            print('Error:', e)
            print('Failed to connect to the database')
            conn.rollback()
            # conn.close()
        finally:
            curs.close()
        sleep(3600)
create_table()
log_stue_data()