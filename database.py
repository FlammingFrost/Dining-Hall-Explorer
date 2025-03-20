import sqlite3
from typing import List, Dict, Any

# Database file
DB_FILE = "data/dining_hall_menu.db"

# Step 1: Initialize Database
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

        -- Nutritional Content (0-10 scale)
        contains_vegetable BOOLEAN,
        fiber_level INTEGER,  
        fat_level INTEGER,    
        protein_level INTEGER,
        carb_level INTEGER,   
        sodium_level INTEGER,
        sugar_level INTEGER,

        -- Protein Source Breakdown
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

if __name__ == "__main__":
    initialize_database()
    
    # Test the database
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
                   select distinct dish_name, beef_part from menu_items
                   where have_beef = 1 and dining_hall = 'Arrillaga Family Dining Commons' and beef_part != 'Ground';
                   """
                )
    print(cursor.fetchall())
    conn.close()