import os
import sqlite3
import json
import subprocess
from datetime import datetime

# OpenAI API Key (Replace with your own securely stored key)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Database file
DB_FILE = "data/dining_hall_menu.db"

# Current date, without leading zeros on month and day
CURRENT_DATE = datetime.now().strftime("%m-%d-%Y").lstrip("0").replace("-0", "-")

# few-shot examples and prompt
def load_few_shot_examples(file_path):
    """Read few-shot examples from a text file and return as a string."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()
def load_prompt(file_path):
    """Read the prompt from a text file and return as a string."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()
FEW_SHOT_EXAMPLES = load_few_shot_examples("data/prompt_engineer/few_shot_sql.txt")
PROMPT = load_prompt("data/prompt_engineer/prompt_sql.txt")

def validate_sql_query(sql_query, natural_language_query):
    """
    Validate the generated SQL query using OpenAI API and provide advice if it is not valid.
    """
    prompt = f"""
    Validate the following SQL query based on the natural language query provided. 
    If the SQL query is valid, respond with "VALID". 
    Does not filter for some conditions is ACCEPTABLE.
    No need to check the correctness of the names, only check if the overall logic makes sense.
    You should be very unlikely to invalidate queries. If INVALID, provide a specific reason why the query is invalid in 2-3 sentences.

    Natural Language Query: "{natural_language_query}"
    SQL Query: "{sql_query}"

    Response:
    """
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are an expert SQL validator."},
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

    try:
        response = subprocess.run(curl_command, shell=True, capture_output=True, text=True, timeout=30)
        output_text = response.stdout.strip()
        response_json = json.loads(output_text)
        validation_response = response_json["choices"][0]["message"]["content"].strip()

        if validation_response.upper() == "VALID":
            return True, None
        else:
            return False, validation_response
    except Exception as e:
        print(f"Error validating SQL query: {e}")
        return False, "An error occurred while validating the SQL query."

def generate_sql_query(natural_language_query, context=""):
    """Generate SQL query from natural language using OpenAI API."""
    prompt = f"""
    Understand the natural language query and generate the corresponding SQL query that retrieves the relevant data.
    
    {PROMPT}
    ### Notes:
    - Only query necessary columns based on the question.
    - CURRENT_DATE is '{CURRENT_DATE}'. Only include rows where the date is '{CURRENT_DATE}' or later, unless specified otherwise.
    - Limit the number of results to 50.
    - Dining_hass, meals, beef_part, pork_part, and chicken_part is enums.
    
    ### Few-Shot Examples:
    {FEW_SHOT_EXAMPLES}
    Context: "{context}"
    Query: "{natural_language_query}"
    SQL:
    """
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are an expert SQL generator."},
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

    try:
        response = subprocess.run(curl_command, shell=True, capture_output=True, text=True, timeout=30)
        output_text = response.stdout.strip()
        response_json = json.loads(output_text)
        sql_query = response_json["choices"][0]["message"]["content"].strip().replace("```sql", "").replace("```", "").replace("```SQL", "")
        return sql_query
    except Exception as e:
        print(f"Error generating SQL query: {e}")
        print(f"Response: {response.stdout.strip()}")
        return None

def execute_sql_query(conn, sql_query):
    """Execute the SQL query on the database and return results."""
    try:
        cursor = conn.cursor()
        cursor.execute(sql_query)
        results = cursor.fetchall()
        return results
    except sqlite3.Error as e:
        print(f"Error executing SQL query: {e}")
        return None

def generate_response_from_results(results, natural_language_query):
    """
    Generate a human-readable response from SQL query results.
    
    Combine the SQL query results with the original natural language query to generate a response.
    """
    if not results:
        return "No data found for your query."

    prompt = f"""
    Based on the following SQL query results, generate a human-readable response:
    Results: {results}
    Query: "{natural_language_query}"
    Response:
    """
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are an expert in generating natural language responses from structured data."},
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

    try:
        response = subprocess.run(curl_command, shell=True, capture_output=True, text=True, timeout=30)
        output_text = response.stdout.strip()
        response_json = json.loads(output_text)
        response_text = response_json["choices"][0]["message"]["content"].strip()
        return response_text
    except Exception as e:
        print(f"Error generating response: {e}")
        return "An error occurred while generating the response."

MAX_ATTEMPTS = 5
def handle_query(natural_language_query):
    """Handle the full pipeline: NL query -> SQL -> Execute -> Response."""
    print(f"Processing query: {natural_language_query}")
    
    additional_advice = ""
    attempt = 0
    while attempt <= MAX_ATTEMPTS:
        attempt += 1
        print(f"Attempt {attempt} to process the query.")
        
        sql_query = generate_sql_query(natural_language_query, additional_advice)
        if not sql_query:
            print("Failed to generate SQL query. Retrying...")
            continue

        print(f"Generated SQL Query: {sql_query}")
        # is_valid, advice = validate_sql_query(sql_query, natural_language_query)
        # if not is_valid:
        #     print(f"SQL Query Validation Failed. Giving advice: {advice}")
        #     additional_advice = f"- {advice}"
        #     continue
        results = execute_sql_query(sqlite3.connect(DB_FILE), sql_query)
        if len(results) == 0:
            print("Received empty results. Retrying...")
            continue
        print(f"SQL Query Results: {results}")
        response = generate_response_from_results(results, natural_language_query)
        if response == "An error occurred while generating the response.":
            print("Failed to generate response. Retrying...")
            continue
        return response

    return "Failed to process the query after {MAX_ATTEMPTS} attempts. Please try again later."

if __name__ == "__main__":
    user_query = input("Enter your query: ")
    response = handle_query(user_query)
    print(response)