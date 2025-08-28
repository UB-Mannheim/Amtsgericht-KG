import os
import json
import requests
from glob import glob
import logging
import re
from pathlib import Path

# ---------------- Logging ----------------
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# ---------------- Ollama Setup ----------------
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:12b")

# ---------------- Google Generative AI Setup ----------------
import google.generativeai as genai

GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    GEMINI_MODEL = "gemini-1.5-pro"  # can be gemini-1.5-flash for speed
else:
    logging.warning("GOOGLE_API_KEY not set. Gemini will be unavailable.")

# ---------------- Path Setup ----------------
current_file = Path(__file__).resolve()

for parent in current_file.parents:
    if (parent / "data" / "processed" / "DE_newspapers_subset").is_dir():
        BASE_DIR = parent
        break
else:
    raise FileNotFoundError("Could not find 'data/processed/DE_newspapers' in parent directories.")

INPUT_DIR = BASE_DIR / "data" / "processed" / "DE_newspapers"
OUTPUT_DIR = BASE_DIR / "data" / "processed" / "json_processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"BASE_DIR:    {BASE_DIR}")
print(f"INPUT_DIR:   {INPUT_DIR}")
print(f"OUTPUT_DIR:  {OUTPUT_DIR}")

# ---------------- Prompt ----------------
EXTRACTION_PROMPT = """
You are given a very crucial preprocessed block of text extracted from a historical German newspaper (1930s).
Go through all the text and understand it with the context.
Extract all instances of the following structured information carefully, if present:
- Court_name
- Date_of_article
- Company_name (if any)
- Registration_Code (if any) - usually this is followed by Handelsregister with abteilung A, B, etc. (e.g. 'Handels register A 238' is HRA 238) 
- Registration_year (if any)

Respond only in JSON format with keys:
Court_name, Date_of_article, Company_name, Registration_Code, Registration_year.
The ideal response would be structured like this:  
{
  "Court_name": "Amtsgericht ABC",
  "Date_of_article": "30. Juni 1939",
  "Company_name": "XYZ G. m. b. H.",
  "Registration_Code": "HRB 123",
  "Registration_year": "1939"
}
{
  "Court_name": "Amtsgericht PQR",
  "Date_of_article": "01. Februar 1937",
  "Company_name": "MNS G. m. b. H.",
  "Registration_Code": "HRA 456",
  "Registration_year": "1932"
}
Do not include ```json or any Markdown formatting.
Do not include explanations.
Only return valid JSON objects.
If a value is not available, set it to null.
"""

# ---------------- Model Selection ----------------
MODEL_BACKEND = os.getenv("MODEL_BACKEND", "ollama")  # "ollama" or "gemini"

def extract_info_with_ollama(text):
    """Extract structured info using Ollama local model"""
    system_message = "You extract structured legal data from historical German newspaper entries."
    user_message = EXTRACTION_PROMPT.strip() + "\n\n" + text.strip()

    data = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.2,
        "stream": False
    }

    response = requests.post(f"{OLLAMA_URL}/chat", json=data)
    if response.status_code != 200:
        raise Exception(f"Ollama API error: {response.text}")
    return response.json()["message"]["content"]

def extract_info_with_gemini(text):
    """Extract structured info using Google Gemini"""
    if not GEMINI_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY is not set. Cannot use Gemini backend.")

    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content(EXTRACTION_PROMPT.strip() + "\n\n" + text.strip())
    return response.text

def extract_info_from_text(text):
    if MODEL_BACKEND == "gemini":
        logging.info("Using Gemini API...")
        return extract_info_with_gemini(text)
    else:
        logging.info("Using Ollama API...")
        return extract_info_with_ollama(text)

# ---------------- Chunking ----------------
def chunk_text_with_overlap(text, max_words=4000, overlap_words=50):
    """Split long text into overlapping word-based chunks"""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = words[i:i + max_words]
        chunks.append(" ".join(chunk))
        i += max_words - overlap_words
    return chunks

# ---------------- Batch Processing ----------------
def batch_extract_entities(input_folder, output_folder):
    text_files = glob(os.path.join(input_folder, "*.txt"))
    logging.info(f"Found {len(text_files)} processed text files.")

    for file_path in text_files:
        filename = os.path.basename(file_path)
        output_filename = filename.replace("_processed.txt", "_entities.json")
        output_path = os.path.join(output_folder, output_filename)

        if os.path.exists(output_path):
            logging.info(f"Skipping already processed: {output_filename}")
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read().strip()

            if not text:
                logging.warning(f"Empty file: {filename}")
                continue

            chunks = chunk_text_with_overlap(text)
            logging.info(f"Extracting from {filename} in {len(chunks)} chunks")

            all_matches = []
            for idx, chunk in enumerate(chunks):
                logging.info(f"Processing chunk {idx+1}/{len(chunks)}")
                result = extract_info_from_text(chunk)
                matches = re.findall(r'{[\s\S]*?}', result)
                all_matches.extend(matches)

            if not all_matches:
                logging.warning(f"No JSON entities found in {filename}")
                continue

            json_array_str = "[" + ",\n".join(all_matches) + "]"
            try:
                json_data = json.loads(json_array_str)
            except json.JSONDecodeError as e:
                logging.error(f"JSON parsing error in {filename}: {e}\nRaw:\n{json_array_str}")
                continue

            with open(output_path, "w", encoding="utf-8") as out:
                json.dump(json_data, out, ensure_ascii=False, indent=2)

            logging.info(f"Saved: {output_filename}")

        except Exception as e:
            logging.error(f"Error processing {filename}: {e}")

# ---------------- Run ----------------
if __name__ == "__main__":
    batch_extract_entities(INPUT_DIR, OUTPUT_DIR)
