import json
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Constants
URL = "https://rdeapps.stanford.edu/dininghallmenu/"
OUTPUT_DIR = "data/stanford_dining_menus"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Function to initialize Selenium WebDriver
def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    # if on macOS
    # return webdriver.Chrome(options=options)
    options.binary_location = "/usr/bin/chromium"
    return webdriver.Chrome(service=webdriver.chrome.service.Service("/usr/bin/chromedriver"), options=options)


# Function to get available dates, dining halls, and meals
def get_available_options(update_only=True) -> tuple:
    driver = init_driver()
    driver.get(URL)
    wait = WebDriverWait(driver, 15)

    print("Fetching available options...")

    # Extract all dining halls
    dining_hall_dropdown = Select(wait.until(EC.presence_of_element_located((By.ID, "MainContent_lstLocations"))))
    dining_halls = [option.text for option in dining_hall_dropdown.options if option.text.strip()]

    # Extract all available dates (within 7 days)
    day_dropdown = Select(wait.until(EC.presence_of_element_located((By.ID, "MainContent_lstDay"))))
    dates = {option.text: option.get_attribute("value") for option in day_dropdown.options if option.get_attribute("value").strip()}

    # Extract all meal types
    meal_dropdown = Select(wait.until(EC.presence_of_element_located((By.ID, "MainContent_lstMealType"))))
    meals = [option.text for option in meal_dropdown.options if option.text.strip()]

    driver.quit()  # Close WebDriver

    print(f"Dining Halls: {dining_halls}")
    print(f"Dates: {list(dates.keys())}")
    print(f"Meal Types: {meals}")

    # Filter out already stored JSON files if update_only=True
    if update_only:
        filtered_dates = {}
        filtered_meals = []
        
        for date_label, date_value in dates.items():
            for meal in meals:
                filename = f"{date_value.replace('/', '-')}-{meal}.json"
                filepath = os.path.join(OUTPUT_DIR, filename)
                
                if not os.path.exists(filepath):
                    filtered_dates[date_label] = date_value
                    filtered_meals.append(meal)

        print(f"Skipping already stored menus. Remaining to scrape: {len(filtered_dates)} dates, {len(filtered_meals)} meals.")
        return filtered_dates, dining_halls, list(set(filtered_meals))  # Ensure unique meal types

    return dates, dining_halls, meals

# Function to scrape menus based on lists of dates, dining halls, and meals
def scrape_menus(dates, dining_halls, meals) -> list[str]:
    driver = init_driver()
    
    saved_files = []
    for date_label, date_value in dates.items():
        for meal in meals:
            filename = f"{date_value.replace('/', '-')}-{meal}.json"
            filepath = os.path.join(OUTPUT_DIR, filename)
            if os.path.exists(filepath):
                print(f"Skipping {filepath}. Already exists.")
                continue

            # Dictionary to store all dining hall menus for this date-meal combination
            day_meal_data = {}

            for dining_hall in dining_halls:
                print(f"Scraping {dining_hall} on {date_label} ({meal})...")

                driver.get(URL)
                wait = WebDriverWait(driver, 15)

                # Select Dining Hall
                dining_hall_dropdown = Select(wait.until(EC.presence_of_element_located((By.ID, "MainContent_lstLocations"))))
                dining_hall_dropdown.select_by_visible_text(dining_hall)
                time.sleep(0.1)

                # Select Day
                day_dropdown = Select(wait.until(EC.presence_of_element_located((By.ID, "MainContent_lstDay"))))
                day_dropdown.select_by_value(date_value)
                time.sleep(0.1)

                # Select Meal
                meal_dropdown = Select(wait.until(EC.presence_of_element_located((By.ID, "MainContent_lstMealType"))))
                meal_dropdown.select_by_visible_text(meal)
                time.sleep(0.5)

                # Extract menu items
                menu_items = driver.find_elements(By.CLASS_NAME, "clsMenuItem")
                menu_data = []

                if menu_items:
                    for item in menu_items:
                        # Dish name
                        dish_name = item.find_element(By.CLASS_NAME, "clsLabel_Name").text.strip()

                        # Ingredients
                        try:
                            ingredients = item.find_element(By.CLASS_NAME, "clsLabel_Ingredients").text.replace("Ingredients:", "").strip()
                        except:
                            ingredients = "N/A"

                        # Allergens
                        try:
                            allergens = item.find_element(By.CLASS_NAME, "clsLabel_Allergens").text.replace("Allergens:", "").strip()
                        except:
                            allergens = "N/A"

                        # Trace Allergens
                        try:
                            trace_allergens = item.find_element(By.CLASS_NAME, "clsLabel_TraceAllergens").text.replace("Made on shared equipment with", "").strip()
                        except:
                            trace_allergens = "N/A"

                        # Dietary Icons
                        dietary_icons = []
                        icon_elements = item.find_elements(By.CLASS_NAME, "clsLabel_IconImage")
                        for icon in icon_elements:
                            dietary_icons.append(icon.get_attribute("alt"))  # Extracts "Gluten Free", "Vegan", etc.

                        # Store structured data
                        menu_data.append({
                            "dish_name": dish_name,
                            "ingredients": ingredients,
                            "allergens": allergens,
                            "trace_allergens": trace_allergens,
                            "dietary_icons": dietary_icons
                        })
                
                # Store data in dictionary
                day_meal_data[dining_hall] = menu_data

            # Save structured data as JSON
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(day_meal_data, f, indent=4, ensure_ascii=False)
            print(f"Saved data to {filepath}")
            saved_files.append(filepath)

    driver.quit()
    print("Scraping completed successfully!")
    return saved_files

# **Usage Example**
if __name__ == "__main__":
    # Step 1: Get available options
    dates_to_scrape, dining_halls, meals_to_scrape = get_available_options(update_only=False)

    # Step 2: Scrape only missing data
    if dates_to_scrape and meals_to_scrape:
        scrape_menus(dates_to_scrape, dining_halls, meals_to_scrape)
    else:
        print("All menus are up to date!")