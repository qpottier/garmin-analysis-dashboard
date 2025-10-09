
import os
from functions import create_database, get_filtered_activity_data, populate_tables, populate_sleep_table, get_sleep_data

# --- Configuration ---
# Define the project root directory (one level up from this script's location)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Define paths relative to the project root for clarity
DATABASE_FILE = os.path.join(PROJECT_ROOT, "garmin_data.db")
FIT_FILES_DIRECTORY = os.path.join(PROJECT_ROOT, 'HealthData/FitFiles/Activities/')
SLEEP_FILES_DIRECTORY = os.path.join(PROJECT_ROOT, 'HealthData/Sleep/')


def main():
    """
    Main function to coordinate the database creation and data import process.
    """
    # 1. Create the database and tables using the absolute path
    if not os.path.exists(DATABASE_FILE):
        print(f"Database file '{DATABASE_FILE}' does not exist. Creating a new database.")
        create_database(DATABASE_FILE)


    # 2. Get the list of .fit files
    fit_files = [f for f in os.listdir(FIT_FILES_DIRECTORY) if f.endswith('.fit')]

    if not fit_files:
        print(f"No .fit files found in '{FIT_FILES_DIRECTORY}'")
        return

    # Keep track of processed files
    imported_files_count = 0
    skipped_files_count = 0

    # 3. Process each .fit file and populate the database
    for fit_file in fit_files:
        file_path = os.path.join(FIT_FILES_DIRECTORY, fit_file)
        print(f"\n--- Processing File: {fit_file} ---")

        extracted_data = get_filtered_activity_data(file_path)

        if extracted_data:
            # Pass the database file path to the populate function
            if populate_tables(extracted_data, DATABASE_FILE):
                imported_files_count += 1
            else:
                skipped_files_count += 1
        else:
            print(f"Could not extract data from {fit_file}.")
            skipped_files_count += 1
    
    # --- 4. Process Sleep Data ---
    print("\n\n--- Starting Sleep Data Import ---")
    sleep_files = [f for f in os.listdir(SLEEP_FILES_DIRECTORY) if f.startswith('sleep_') and f.endswith('.json')]

    if not sleep_files:
        print(f"No sleep files found in '{SLEEP_FILES_DIRECTORY}'")
    else:
        imported_sleep_count = 0
        skipped_sleep_count = 0
        for sleep_file in sleep_files:
            file_path = os.path.join(SLEEP_FILES_DIRECTORY, sleep_file)
            sleep_data = get_sleep_data(file_path)
            # Print all global infos of the ongoing night
            print(f"Global sleep info for {sleep_file}:")
            for key, value in sleep_data.items():
                print(f"  {key}: {value}")
            #print(f"\n--- HRV for this file {sleep_file} is {sleep_data.get('avg_overnight_hrv')} ---")

            if sleep_data:
                if populate_sleep_table(sleep_data, DATABASE_FILE):
                    imported_sleep_count += 1
                else:
                    skipped_sleep_count += 1
        
        print(f"\nSleep import complete. Imported: {imported_sleep_count}, Skipped: {skipped_sleep_count}")


    # --- Final Summary ---
    print("\n\n--- Import Complete ---")
    print(f"Total files processed: {len(fit_files)}")
    print(f"New activities imported: {imported_files_count}")
    print(f"Skipped (already exist): {skipped_files_count}")


if __name__ == "__main__":
    main()