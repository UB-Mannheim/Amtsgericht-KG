import os
import json
from glob import glob
from groq import Groq
import logging

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
# Groq API key setup
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is not set. Please set it to use the Groq API.")

# Initialize Groq client with API key
client = Groq(api_key=GROQ_API_KEY)

# Input directory
INPUT_DIR = "/mnt/c/Users/abhijain/Documents/KG4CR/data/processed/DE_newspapers"

# Prompt instruction
EXTRACTION_PROMPT = """
You are given a very crucial preprocessed block of text extracted from a historical German newspaper (1930s).
Go through all the text and understand it with the context.
Extract the following structured information carefully, if present:
- Court_name
- Date_of_article
- Company_name (if any)
- Registration_Code (if any)
- Registration_year (if any)

Respond only in JSON format with keys:
Court_name, Date_of_article, Company_name, Registration_Code, Registration_year.
If a value is not available, set it to null. Do not return anything other than the JSON response.
"""

def extract_info_from_text(text):
    completion = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {"role": "system", "content": "You extract structured legal data from historical German newspaper entries."},
            {"role": "user", "content": EXTRACTION_PROMPT.strip() + "\n\n" + text.strip()},
        ],
        temperature=0.2,
        max_completion_tokens=1024,
        top_p=1,
        stream=False,
    )
    return completion.choices[0].message.content

def batch_extract_entities(input_folder):
    text_files = glob(os.path.join(input_folder, "**", "*_processed.txt"), recursive=True)
    logging.info(f"Found {len(text_files)} processed text files.")

    for file_path in text_files:
        base = os.path.splitext(file_path)[0]
        output_json_path = base + "_entities.json"

        if os.path.exists(output_json_path):
            logging.info(f"Skipping already processed: {output_json_path}")
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read().strip()

            if not text:
                logging.warning(f"Empty file: {file_path}")
                continue

            logging.info(f"Extracting from: {file_path}")
            result = extract_info_from_text(text)
            # log result for debugging
            logging.debug(f"Raw extraction result: {result}")

            try:
                json_data = json.loads(result)
            except json.JSONDecodeError:
                logging.error(f"Failed to parse JSON from response in {file_path}:\n{result}")
                continue

            with open(output_json_path, "w", encoding="utf-8") as out:
                json.dump(json_data, out, ensure_ascii=False, indent=2)

            logging.info(f"Saved: {output_json_path}")

        except Exception as e:
            logging.error(f"Error processing {file_path}: {e}")

if __name__ == "__main__":
    batch_extract_entities(INPUT_DIR)
