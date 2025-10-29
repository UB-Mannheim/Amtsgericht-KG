import os
import json
from tqdm import tqdm

# Get the absolute path to the project root (two levels up from this script)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Define input and output folders relative to the project structure
input_folder = os.path.join(BASE_DIR, "data", "processed", "downloads_processed")
output_file = os.path.join(BASE_DIR, "data", "processed", "json_combined", "merged_output.json")

merged_data = []

# Ensure the output directory exists
os.makedirs(os.path.dirname(output_file), exist_ok=True)

# List all JSON files
json_files = [f for f in os.listdir(input_folder) if f.endswith(".json")]

# Merge with progress bar
for filename in tqdm(json_files, desc="Merging JSON files", unit="file"):
    file_path = os.path.join(input_folder, filename)
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            if isinstance(data, list):
                merged_data.extend(data)
            else:
                print(f"⚠️ Skipping {filename}: not a list at top level.")
        except json.JSONDecodeError as e:
            print(f"❌ Error reading {filename}: {e}")

# Write to output JSON
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(merged_data, f, ensure_ascii=False, indent=2)

print(f"\n✅ Merged {len(merged_data)} records into:\n{output_file}")
