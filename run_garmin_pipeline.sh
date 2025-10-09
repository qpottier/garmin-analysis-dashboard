#!/bin/bash

# --- Configuration ---
# Navigate to the garmin_project directory
cd "$(dirname "$0")"

# --- Main Logic ---
# Check if the database file exists
if [ ! -f "garmin_data.db" ]; then
    echo "Database not found. Performing initial full download..."
    garmindb_cli.py --activities --sleep --download
else
    echo "Database found. Downloading latest data..."
    garmindb_cli.py --activities --sleep --latest --download
fi


# Run the Python script to populate the database
echo "Running database import script..."
python3 scripts/main.py

# Clean up HealthData directory if it exists
#rm -rf HealthData # Remove existing HealthData directory if it exists

echo "Garmin pipeline finished."