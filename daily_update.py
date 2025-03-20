from scraper import get_available_options, scrape_menus
from etl import *
import sqlite3

DATABASE_FILE = "data/dining_hall_menu.db"  # SQLite database file
DATA_DIR = "data/stanford_dining_menus"  # Directory where scraped menu JSON


def run_daily_update(update_only=True):
    """Runs the full pipeline to update menu information into the database."""
    print("Starting Daily Menu Update Pipeline...")

    # Step 1: Get available menu data to scrape
    dates_to_scrape, dining_halls, meals_to_scrape = get_available_options(update_only=update_only)

    if not dates_to_scrape:
        print("No new menu data to scrape. Exiting.")
        return

    print(f"Scraping data for dates: {dates_to_scrape}")

    # Step 2: Scrape menu data
    updated_files = scrape_menus(dates_to_scrape, dining_halls, meals_to_scrape)
    print("Menu data scraped and stored successfully.")

    # Step 3: Load newly scraped menu data
    print("Loading scraped menu data...")
    menu_data_files = load_scraped_data(updated_files)

    if not menu_data_files:
        print("No new menu data found. Exiting.")
        return

    # Step 4: Process each menu entry
    conn = sqlite3.connect(DATABASE_FILE)
    
    for raw_menu_item in menu_data_files:

        # Step 5: Transform data using OpenAI API
        transformed_data = transform_menu_item(**raw_menu_item)
        if not transformed_data:
            print(f"Skipping: {raw_menu_item['data']['dish_name']}")
            continue

        # Step 6: Insert transformed data into database
        if insert_or_update_record(conn, transformed_data):
            # print(f"Inserted: {raw_menu_item['data']['dish_name']}")
            pass
        else:
            print(f"Failed to insert: {raw_menu_item['data']['dish_name']}")
            
    conn.close()
    print("Daily update process completed successfully.")

def __refresh_database():
    """Helper function to refresh the database by deleting all entries."""
    conn = sqlite3.connect(DATABASE_FILE)
    # Delete all entries
    # cursor.execute("DELETE FROM menu_items;")
    # conn.commit()
    
    # Insert all scraped data
    import os
    import json
    for filename in os.listdir(DATA_DIR):
        with open(os.path.join(DATA_DIR, filename), "r", encoding="utf-8") as f:
            menu_data = json.load(f)
            for dining_hall, menu_items in menu_data.items():
                print(f"Processing {filename} for {dining_hall}...")
                date = '-'.join(filename.replace(".json", "").split("-")[:3])
                meal = filename.replace(".json", "").split("-")[3]
                for item in menu_items: # each item is a dish, dictionary
                    if item:
                        record_id = check_existing_record(conn, date, meal, dining_hall, item['dish_name'])
                        if record_id:
                            pass
                        else:
                            transformed_data = transform_menu_item(date, meal, dining_hall, item)
                            insert_or_update_record(conn, transformed_data)
    conn.commit()
    conn.close() 

    print("Database refreshed.")

if __name__ == "__main__":
    # run_daily_update(update_only=False)
    __refresh_database()  # Uncomment to refresh the database with all scraped data
