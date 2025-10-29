import requests
import os
import re

# --- Parameters ---
YEAR_MIN = 1922
YEAR_MAX = 1945
LIST_URL = "https://digi.bib.uni-mannheim.de/~stweil/Amtsgericht_Fundstellen.txt"
BASE_URL = "https://digi.bib.uni-mannheim.de/periodika/fileadmin/data/"
DOWNLOAD_DIR = "data/raw_data/DE_newspapers"  ## update this as needed

# --- Fetch list of filenames ---
print("📥 Fetching list of all files...")
resp = requests.get(LIST_URL, headers={"User-Agent": "Mozilla/5.0"})
resp.raise_for_status()
all_filenames = [line.strip() for line in resp.text.splitlines() if line.strip()]
total_files = len(all_filenames)
print(f"✅ Total files listed: {total_files}")

# --- Filter by year ---
print(f"\n🔍 Filtering files from {YEAR_MIN} to {YEAR_MAX}...")
pattern = re.compile(r'(1[89]\d{2}|20\d{2})')
filtered_files = []

for name in all_filenames:
    matches = pattern.findall(name)
    if not matches:
        continue
    chosen_year = int(matches[-1])
    if YEAR_MIN <= chosen_year <= YEAR_MAX:
        filtered_files.append(name)

print(f"✅ Found {len(filtered_files)} files in date range {YEAR_MIN}-{YEAR_MAX}\n")

if len(filtered_files) == 0:
    print("❌ No files to download. Exiting.")
    exit()

# --- Prepare folder ---
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# --- Download loop ---
success_count = 0
fail_count = 0
skipped_count = 0

for i, name in enumerate(filtered_files, start=1):
    file_url = BASE_URL + name
    
    # Extract year from filename
    matches = pattern.findall(name)
    year = matches[-1] if matches else "unknown"
    
    # Create year-based folder structure
    year_folder = os.path.join(DOWNLOAD_DIR, year)
    os.makedirs(year_folder, exist_ok=True)
    
    # Save with just the filename (not full path)
    local_path = os.path.join(year_folder, os.path.basename(name))
    
    # Check if file already exists
    if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
        print(f"[{i}/{len(filtered_files)}] ⏭️  Already exists: {os.path.basename(name)} (Year: {year})")
        skipped_count += 1
        continue
    
    print(f"[{i}/{len(filtered_files)}] ➡️ Fetching {os.path.basename(name)} (Year: {year})")
    
    try:
        r = requests.get(file_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        if r.status_code == 200 and len(r.content) > 0:
            with open(local_path, "wb") as f:
                f.write(r.content)
            print(f"   ✅ Saved -> {local_path} ({len(r.content)} bytes)")
            success_count += 1
        else:
            print(f"   ⚠️ Skipped (status {r.status_code}, empty or missing)")
            fail_count += 1
    except requests.RequestException as e:
        print(f"   ❌ Error: {e}")
        fail_count += 1

print(f"\n{'='*60}")
print(f"🏁 DOWNLOAD COMPLETE!")
print(f"{'='*60}")
print(f"✅ Successfully downloaded: {success_count} files")
print(f"❌ Failed/Skipped: {fail_count} files")
print(f"📁 Location: {os.path.abspath(DOWNLOAD_DIR)}")
print(f"{'='*60}")