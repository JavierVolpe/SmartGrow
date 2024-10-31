#!/bin/bash

# Get current timestamp
timestamp=$(date +"%Y%m%d_%H%M%S")

# Define the path where the photo will be saved
photo_path="/home/javier/SmartHome/static/${timestamp}.jpg"

# Take the photo with 180-degree rotation
rpicam-jpeg -o $photo_path --rotation 180

