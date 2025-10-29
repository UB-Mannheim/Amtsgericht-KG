import re
import requests
from collections import Counter
import os

LIST_URL = "https://digi.bib.uni-mannheim.de/~stweil/Amtsgericht_Fundstellen.txt"
YEAR_MIN = 1922
YEAR_MAX = 1945

# fetch
resp = requests.get(LIST_URL, headers={"User-Agent": "Mozilla/5.0"})
resp.raise_for_status()
filenames = [line.strip() for line in resp.text.splitlines() if line.strip()]

print(f"Total filenames fetched: {len(filenames)}")

# match any 4-digit year in 1800-2099 (no word-boundaries)
pattern = re.compile(r'(1[89]\d{2}|20\d{2})')

year_counter = Counter()
in_range_files = []

for name in filenames:
    # if you want to prefer the basename (ignore directory-prefix dates), use:
    # candidate = os.path.basename(name)
    # matches = pattern.findall(candidate)
    # but here we use the full path and choose the last match
    matches = pattern.findall(name)
    if not matches:
        continue
    # choose the last match (closest to filename/basename in typical paths)
    chosen_year = int(matches[-1])
    year_counter[chosen_year] += 1
    if YEAR_MIN <= chosen_year <= YEAR_MAX:
        in_range_files.append(name)

total_with_year = sum(year_counter.values())
print(f"Filenames that contain any 4-digit year (1800-2099): {total_with_year}")
print(f"Filenames with chosen year in range {YEAR_MIN}-{YEAR_MAX}: {len(in_range_files)}\n")

# per-year breakdown (only for the requested range)
print("Counts per year in range:")
for y in range(YEAR_MIN, YEAR_MAX + 1):
    if year_counter.get(y):
        print(f"  {y}: {year_counter[y]}")

# show some examples
print("\nSample filenames in range (up to 20):")
for sample in in_range_files[:20]:
    print(" ", sample)
