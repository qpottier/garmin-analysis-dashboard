import psycopg2
import os
from dotenv import load_dotenv
from fitparse import FitFile
from datetime import datetime
import json

load_dotenv()




def get_db_connection():
    """Établit et retourne une connexion à la base de données PostgreSQL en utilisant l'URL du fichier .env."""
    conn_str = os.getenv("DATABASE_URL")
    if not conn_str:
        raise ValueError("La variable d'environnement DATABASE_URL n'est pas définie. Veuillez la créer dans votre fichier .env.")
    return psycopg2.connect(conn_str)

# --- Database Schema ---
def create_database():
    """Creates the PostgreSQL database and all necessary tables."""
    con = get_db_connection()
    with con.cursor() as cur:
        # Users table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            full_name TEXT,
            garmin_display_name TEXT
        );
        """)

        # Activities Table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            activity_id BIGINT PRIMARY KEY,
            sport TEXT,
            start_time_gmt TEXT,
            distance_m REAL,
            total_elapsed_time_s REAL,
            total_timer_time_s REAL,
            calories REAL,
            avg_hr REAL,
            max_hr REAL,
            avg_cadence REAL,
            num_laps INTEGER,
            total_ascent REAL,
            total_descent REAL,
            workout_rpe INTEGER,
            workout_feel INTEGER
        );
        """)

        # Laps Table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS laps (
            id SERIAL PRIMARY KEY,
            activity_id BIGINT,
            lap_number INTEGER,
            start_time_gmt TEXT,
            distance_m REAL,
            total_elapsed_time_s REAL,
            total_timer_time_s REAL,
            avg_hr REAL,
            max_hr REAL,
            calories REAL,
            lap_trigger TEXT,
            FOREIGN KEY (activity_id) REFERENCES activities (activity_id)
        );
        """)

        # Sleep Table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS sleep (
            sleep_id TEXT PRIMARY KEY,
            total_sleep_seconds INTEGER,
            deep_sleep_seconds INTEGER,
            light_sleep_seconds INTEGER,
            rem_sleep_seconds INTEGER,
            awake_sleep_seconds INTEGER,
            avg_sleep_stress REAL,
            overall_score INTEGER,
            avg_overnight_hrv REAL,
            resting_heart_rate INTEGER
        );
        """)

        # Records Table (second-by-second data)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS records (
            activity_id BIGINT,
            timestamp TEXT,
            record_number INTEGER,
            heart_rate INTEGER,
            cadence INTEGER,
            distance REAL,
            power INTEGER,
            speed REAL,
            altitude REAL,
            PRIMARY KEY (activity_id, timestamp),
            FOREIGN KEY (activity_id) REFERENCES activities (activity_id)
        );
        """)

        con.commit()
    con.close()
    print("Base de données PostgreSQL prête.")

def add_or_update_user(user_id, full_name, display_name):
    """Ajoute ou met à jour un utilisateur dans la table users."""
    con = get_db_connection()
    with con.cursor() as cur:

        cur.execute("""
            INSERT INTO users (user_id, full_name, garmin_display_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                full_name = EXCLUDED.full_name,
                garmin_display_name = EXCLUDED.garmin_display_name;
        """, (user_id, full_name, display_name))
    con.commit()
    con.close()
    print(f"Utilisateur '{user_id}' ajouté ou mis à jour.")


def get_filtered_activity_data(fit_file_path):
    # ... (this function does not need any changes)
    """
    Parses a .fit file and extracts a filtered set of activity and lap data.
    """
    try:
        fitfile = FitFile(fit_file_path)
    except Exception as e:
        print(f"Error opening or parsing {fit_file_path}: {e}")
        return None

    # --- Define the specific fields you want to keep ---
    activity_fields_to_keep = [
        'start_time','sport', 'total_distance', 'total_elapsed_time',
        'total_timer_time', 'total_calories', 'total_ascent',
        'total_descent', 'avg_heart_rate', 'max_heart_rate',
        'avg_running_cadence', 'num_laps','unknown_193','unknown_192'  # RPE and Feel fields
    ]
    lap_fields_to_keep = [
        'start_time', 'total_distance', 'total_elapsed_time',
        'total_timer_time', 'total_calories', 'avg_heart_rate',
        'max_heart_rate', 'avg_running_cadence', 'lap_trigger'
    ]
    record_fields_to_keep = [
    'timestamp', 'heart_rate', 'cadence', 'distance', 'power',
    'enhanced_speed', 'enhanced_altitude'
    ]

    activity_data = {}
    laps_data = []
    records_data = []

    # Extract data from the .fit file
    for record in fitfile.get_messages(['session', 'lap', 'record']):
        if record.name == 'session':
            for field in record:
                if field.name in activity_fields_to_keep:
                    activity_data[field.name] = field.value
        elif record.name == 'lap':
            lap_info = {}
            for field in record:
                if field.name in lap_fields_to_keep:
                    lap_info[field.name] = field.value
            laps_data.append(lap_info)
        elif record.name == 'record':
            record_info = {}
            for field in record:
                if field.name in record_fields_to_keep:
                    record_info[field.name] = field.value
            # Only add the record if it has data
            if record_info:
                records_data.append(record_info)

           

    # Generate and add the unique activity ID
    if 'start_time' in activity_data:
        activity_id = int(activity_data['start_time'].strftime('%Y%m%d%H%M%S'))
        activity_data['activity_id'] = activity_id
        for lap in laps_data:
            lap['activity_id'] = activity_id
    
    # Ensure activity_id is always present in the dictionary key
    if 'activity_id' not in activity_data and laps_data:
        # Fallback to lap start time if session message is missing start_time
        first_lap_start_time = laps_data[0].get('start_time')
        if first_lap_start_time:
             activity_id = int(first_lap_start_time.strftime('%Y%m%d%H%M%S'))
             activity_data['activity_id'] = activity_id


    return {
        "activity": activity_data,
        "laps": laps_data,
        "records": records_data
    }










def populate_tables(data):
    """Populates the database tables with activity and lap data."""
    if not data or not data.get('activity'):
        return False
    
    act = data['activity']
    activity_id = act.get('activity_id')
    
    if not activity_id:
        return False

    con = get_db_connection()


    with con.cursor() as cur:

        # --- Security Check: See if activity_id already exists ---
        cur.execute("SELECT activity_id FROM activities WHERE activity_id = %s ", (activity_id,))
        if cur.fetchone():
            print(f"Activity {activity_id} already exists in the database. Skipping.")
            con.close()
            return False

        # --- Insert Activity Data ---
        cur.execute("""
            INSERT INTO activities (
                activity_id, sport, start_time_gmt, distance_m, 
                total_elapsed_time_s, total_timer_time_s, calories, 
                avg_hr, max_hr, avg_cadence, num_laps, total_ascent, total_descent, workout_rpe, workout_feel
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            act.get('activity_id'),
            act.get('sport'),
            act.get('start_time'),
            act.get('total_distance'),
            act.get('total_elapsed_time'),
            act.get('total_timer_time'),
            act.get('total_calories'),
            act.get('avg_heart_rate'),
            act.get('max_heart_rate'),
            act.get('avg_running_cadence'),
            act.get('num_laps'),
            act.get('total_ascent'),
            act.get('total_descent'),
            act.get('unknown_193'),  # workout_rpe
            act.get('unknown_192')   # workout_feel
        ))

    # --- Insert Lap Data ---
        for i, lap in enumerate(data.get('laps', []), 1):
            cur.execute("""
                INSERT INTO laps (
                    activity_id, lap_number, start_time_gmt, distance_m, 
                    total_elapsed_time_s, total_timer_time_s, avg_hr, 
                    max_hr, calories, lap_trigger
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                lap.get('activity_id'),
                i,
                lap.get('start_time'),
                lap.get('total_distance'),
                lap.get('total_elapsed_time'),
                lap.get('total_timer_time'),
                lap.get('avg_heart_rate'),
                lap.get('max_heart_rate'),
                lap.get('total_calories'),
                lap.get('lap_trigger')
            ))

        # --- Insert Record Data ---
        records = data.get('records', [])
        if records:
            records_to_insert = []
            for i, rec in enumerate(records, 1):
                records_to_insert.append((
                    activity_id,
                    rec.get('timestamp'),
                    i, # This is the new record_number
                    rec.get('heart_rate'),
                    rec.get('cadence'),
                    rec.get('distance'),
                    rec.get('power'),
                    rec.get('enhanced_speed'),
                    rec.get('enhanced_altitude')
                ))
            cur.executemany("""
                INSERT INTO records (activity_id, timestamp, record_number, heart_rate, cadence, distance, power, speed, altitude)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (activity_id, timestamp) DO NOTHING;
            """, records_to_insert)



    con.commit()
    con.close()
    print(f"Data for activity {activity_id} imported successfully.")
    return True

def get_sleep_data(json_file_path):
    """Parses a sleep JSON file and extracts the relevant data."""
    try:
        with open(json_file_path, 'r') as f:
            root_data = json.load(f)
            data = root_data.get('dailySleepDTO', {})
    except (FileNotFoundError, json.JSONDecodeError):
        return None

    if not data:
        return None

    # Use the calendarDate as the unique sleep_id
    sleep_id = data.get('calendarDate')
    if not sleep_id:
        return None

    return {
        "sleep_id": sleep_id,
        "total_sleep_seconds": data.get('sleepTimeSeconds'),
        "deep_sleep_seconds": data.get('deepSleepSeconds'),
        "light_sleep_seconds": data.get('lightSleepSeconds'),
        "rem_sleep_seconds": data.get('remSleepSeconds'),
        "awake_sleep_seconds": data.get('awakeSleepSeconds'),
        "avg_sleep_stress": data.get('avgSleepStress'),
        "overall_score": data.get('sleepScores', {}).get('overall', {}).get('value'),
        "avg_overnight_hrv": root_data.get('avgOvernightHrv'),  # Get from root level
        "resting_heart_rate": root_data.get('restingHeartRate')  # Also root level
    }


def populate_sleep_table(data):
    """Populates the sleep table, checking for duplicates."""
    if not data:
        return False

    con = get_db_connection()
    with con.cursor() as cur:

        # Security Check: See if sleep_id already exists
        cur.execute("SELECT sleep_id FROM sleep WHERE sleep_id = %s", (data['sleep_id'],))
        if cur.fetchone():
            con.close()
            return False # Indicates that the data was skipped

        # Insert Sleep Data
        cur.execute("""
            INSERT INTO sleep (
                sleep_id, total_sleep_seconds, deep_sleep_seconds, light_sleep_seconds, rem_sleep_seconds, awake_sleep_seconds, avg_sleep_stress, overall_score, avg_overnight_hrv, resting_heart_rate
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (sleep_id) DO NOTHING;
        """, (
            data.get('sleep_id'), data.get('total_sleep_seconds'),
            data.get('deep_sleep_seconds'), data.get('light_sleep_seconds'),
            data.get('rem_sleep_seconds'), data.get('awake_sleep_seconds'),
            data.get('avg_sleep_stress'), data.get('overall_score'),
            data.get('avg_overnight_hrv'), data.get('resting_heart_rate')
        ))

    con.commit()
    con.close()
    print(f"Sleep data for {data['sleep_id']} imported successfully.")
    return True # Indicates a successful import