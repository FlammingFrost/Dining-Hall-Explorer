import os
import json
import sqlite3
import subprocess
import hashlib
from datetime import datetime

# OpenAI API Key (Replace with your own securely stored key)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Database file
DB_FILE = "data/dining_hall_menu.db"
DATA_DIR = "data/stanford_dining_menus"  # Directory where scraped menu JSON

# Load few-shot examples and prompt from file
def load_few_shot_examples(file_path: str) -> str:
    """Reads few-shot examples from a text file and returns as a string."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()
def load_prompt(file_path: str) -> str:
    """Reads the prompt from a text file and returns as a string."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

FEW_SHOT_EXAMPLES = load_few_shot_examples("data/prompt_engineer/few_shot_transform.txt")
PROMPT = load_prompt("data/prompt_engineer/prompt_transform.txt")

# In-memory cache to store processed results
TRANSFORM_CACHE = {}

def transform_menu_item(date: str, meal: str, dining_hall: str, data: dict) -> dict:
    """Uses OpenAI API via curl to generate structured nutritional and property data with caching."""

    prompt = f"""
    {PROMPT}
    Use the following few-shot examples as references:

    ### Few-Shot Examples:
    {FEW_SHOT_EXAMPLES}

    ### Input Data:
    {json.dumps(data, indent=2)}
    
    ### Expected Output (JSON):
    """.strip()

    # Generate a hash key based on the full prompt (captures all relevant input)
    prompt_hash = hashlib.md5(prompt.encode("utf-8")).hexdigest()
    date = datetime.strptime(date, "%m-%d-%Y").strftime("%Y-%m-%d")

    # Check cache first
    if prompt_hash in TRANSFORM_CACHE:
        print(f"[Cache Hit] Skipping transformation for: {data['dish_name']}")
        cached_data = TRANSFORM_CACHE[prompt_hash].copy()
        cached_data["date"] = date
        cached_data["meal"] = meal
        cached_data["dining_hall"] = dining_hall
        cached_data["dish_name"] = data["dish_name"]
        cached_data["ingredients"] = data["ingredients"]
        cached_data["original_description"] = json.dumps(data, indent=2)
        return cached_data

    # Prepare the payload
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "developer",
                "content": "You are an AI expert in food science and nutrition. Your task is to analyze a dish based on its ingredients and description and estimate its properties, taste profile, and nutritional levels on a 0-10 scale."
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3
    }
    json_payload = json.dumps(payload, ensure_ascii=False).replace("'", "’")

    curl_command = f"""
    curl https://api.openai.com/v1/chat/completions \
    -H "Authorization: Bearer {OPENAI_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{json_payload}'
    """

    retries = 10
    for attempt in range(1, retries + 1):
        try:
            print(f"[Attempt {attempt}] Transforming: {data['dish_name']}")
            response = subprocess.run(curl_command, shell=True, capture_output=True, text=True, timeout=30)
            output_text = response.stdout.strip()

            response_json = json.loads(output_text)
            structured_output = json.loads(response_json["choices"][0]["message"]["content"])

            # Enrich the result with context
            structured_output["date"] = date
            structured_output["meal"] = meal
            structured_output["dining_hall"] = dining_hall
            structured_output["dish_name"] = data["dish_name"]
            structured_output["ingredients"] = data["ingredients"]
            structured_output["original_description"] = json.dumps(data, indent=2)

            # Cache the result
            TRANSFORM_CACHE[prompt_hash] = structured_output
            return structured_output

        except Exception as e:
            print(f"[Attempt {attempt}] Failed with error: {e}")
            print(f"Response: {response.stdout.strip()}")
            if attempt == retries:
                print("Max retries reached. Returning empty dict.")
                return {}

# Function to insert transformed data into SQLite
def check_existing_record(conn, date: str, meal: str, dining_hall: str, dish_name: str) -> int:
    """
    Checks if a record with the same date, meal, dining hall, and dish name exists in the database.
    
    Returns:
        int: The ID of the existing record if found, otherwise None.
    """
    cursor = conn.cursor()
    check_query = '''
    SELECT id FROM menu_items
    WHERE date = ? AND meal = ? AND dining_hall = ? AND dish_name = ?
    '''
    try:
        cursor.execute(check_query, (date, meal, dining_hall, dish_name))
        existing_record = cursor.fetchone()
        return existing_record[0] if existing_record else None
    except Exception as e:
        print("Error checking existing record:", e)
        import pdb; pdb.set_trace()
        return None

def insert_or_update_record(conn, data: dict, record_id: int = None):
    """Inserts a new record or updates an existing record in the database."""
    cursor = conn.cursor()

    try:
        if record_id:
            # Update the existing record
            query = '''
            UPDATE menu_items
            SET 
                original_description = ?, cuisine = ?, cooking_style = ?, 
                is_sweet = ?, is_savory = ?, is_spicy = ?, contains_vegetable = ?, 
                have_beef = ?, beef_part = ?, have_pork = ?, pork_part = ?, 
                have_chicken = ?, chicken_part = ?, have_fish = ?, fish_part = ?, 
                allergens = ?, dietary_group = ?
            WHERE id = ?
            '''
            values = (
                data.get("original_description", ""), data.get("cuisine", ""), data.get("cooking_style", ""),
                data.get("is_sweet", False), data.get("is_savory", False), data.get("is_spicy", False), 
                data.get("contains_vegetable", False), data.get("have_beef", False), data.get("beef_part", ""), 
                data.get("have_pork", False), data.get("pork_part", ""), data.get("have_chicken", False), 
                data.get("chicken_part", ""), data.get("have_fish", False), data.get("fish_part", ""), 
                str(data.get("allergens", "")), str(data.get("dietary_group", "")), record_id
            )
            cursor.execute(query, values)
        else:
            # Insert a new record
            query = '''
            INSERT INTO menu_items (
                date, meal, dining_hall, dish_name, original_description, cuisine, cooking_style, 
                is_sweet, is_savory, is_spicy, contains_vegetable, have_beef, beef_part, have_pork, 
                pork_part, have_chicken, chicken_part, have_fish, fish_part, allergens, dietary_group
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            values = (
                data["date"], data["meal"], data["dining_hall"], data["dish_name"], 
                data.get("original_description", ""), data.get("cuisine", ""), data.get("cooking_style", ""), 
                data.get("is_sweet", False), data.get("is_savory", False), data.get("is_spicy", False), 
                data.get("contains_vegetable", False), data.get("have_beef", False), data.get("beef_part", ""), 
                data.get("have_pork", False), data.get("pork_part", ""), data.get("have_chicken", False), 
                data.get("chicken_part", ""), data.get("have_fish", False), data.get("fish_part", ""), 
                str(data.get("allergens", "")), str(data.get("dietary_group", ""))
            )
            cursor.execute(query, values)

        conn.commit()
    except KeyError as e:
        print(f"KeyError: Missing key {e} in data: {data}")
    except Exception as e:
        print(f"An error occurred: {e}")

def initialize_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS menu_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATE NOT NULL,
        meal TEXT NOT NULL CHECK(meal IN ('Breakfast', 'Lunch', 'Dinner', 'Brunch')),
        dining_hall TEXT NOT NULL,
        dish_name TEXT NOT NULL,
        original_description TEXT,
        cuisine TEXT,
        cooking_style TEXT,
        
        -- Taste Profile
        is_sweet BOOLEAN,
        is_savory BOOLEAN,
        is_spicy BOOLEAN,

        -- Protein Source Breakdown
        contains_vegetable BOOLEAN,
        have_beef BOOLEAN,
        beef_part TEXT,
        have_pork BOOLEAN,
        pork_part TEXT,
        have_chicken BOOLEAN,
        chicken_part TEXT,
        have_fish BOOLEAN,
        fish_part TEXT,

        -- Dietary Information
        allergens TEXT,
        dietary_group TEXT
    );
    ''')
    
    conn.commit()
    conn.close()

def load_scraped_data(filepaths: list[str]) -> list:
    """
    Reads scraped JSON files and returns a list of dictionaries formatted for database insertion.
    
    Returns:
        List[Dict]: List of menu items with keys (`date`, `meal`, `dining_hall`, `dish_name`, `ingredients`, `allergens`, `trace_allergens`, `dietary_icons`)
    """
    scraped_data = []

    # Iterate through JSON files in the directory
    filenames = [f.split("/")[-1] for f in filepaths if f.endswith(".json")]
    for file_name in filenames:
        file_path = file_name

        # Extract date and meal type from filename
        try:
            date_meal_part = file_name.replace(".json", "").split("-")
            date = '-'.join(date_meal_part[:3])
            meal = date_meal_part[3]
        except IndexError:
            print(f"Skipping invalid filename format: {file_name}")
            continue

        # Read JSON file
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)  # This is a dictionary where keys are dining halls

            for dining_hall, dishes in data.items():
                for dish in dishes:
                    scraped_data.append({
                        "date": date,
                        "meal": meal,
                        "dining_hall": dining_hall,
                        "data": dish
                    })

    return scraped_data

if __name__ == "__main__":
    # Initialize the database
    os.remove(DB_FILE)
    initialize_database()