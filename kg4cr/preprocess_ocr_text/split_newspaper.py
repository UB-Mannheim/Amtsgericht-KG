import os
import re
import logging
from glob import glob

def split_advertisements(text, overlap_lines=2):
    # Normalize whitespace
    text = re.sub(r'\s{2,}', ' ', text)
    text = re.sub(r'\n+', '\n', text.strip())

    # This pattern matches:
    # (1) (City, den 15. Februar 1932.)
    # (2) (City, den 15. Februar 1932. Amtsgericht XYZ.)
    # (3) Amtsgericht City, den 15. Februar 1932.
    # (4) City, den 15. Februar 1932. Amtsgericht XYZ.
    pattern = re.compile(
        r'((?:\(?\s*(?:Amtsgericht\s+)?[A-ZÄÖÜa-zäöüß\- ]+), den \d{1,2}\. [A-ZÄÖÜa-zäöüß]+ \d{4}(?:\. [^)]+)?\)?)',
        re.MULTILINE
    )

    matches = list(pattern.finditer(text))
    ads = []

    for i, match in enumerate(matches):
        start_idx = match.start()
        end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(text)

        # Add overlapping context from the previous ad
        section_text = text[start_idx:end_idx].strip()
        if i > 0 and overlap_lines > 0:
            prev_section = text[matches[i - 1].start():start_idx].strip().splitlines()
            if len(prev_section) >= overlap_lines:
                overlap = "\n".join(prev_section[-overlap_lines:])
                section_text = overlap + "\n" + section_text

        if len(section_text) > 100:
            ads.append(section_text)

    return ads


def process_preprocessed_files(folder_path):
    processed_files = glob(os.path.join(folder_path, "*.txt"))
    logging.info(f"Found {len(processed_files)} files.")

    for file_path in processed_files:
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        ads_folder = os.path.join(folder_path, f"{base_name}_ads")

        os.makedirs(ads_folder, exist_ok=True)
        logging.info(f"\n--- Splitting: {base_name} ---")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            logging.error(f"Failed to read {file_path}: {e}")
            continue

        ads = split_advertisements(text)
        logging.info(f"Identified {len(ads)} advertisement blocks.")

        for i, ad in enumerate(ads, start=1):
            ad_path = os.path.join(ads_folder, f"{base_name}_ad_{i:03}.txt")
            try:
                with open(ad_path, "w", encoding="utf-8") as f:
                    f.write(ad)
            except Exception as e:
                logging.error(f"Failed to save ad {i}: {e}")


# Entry Point
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    INPUT_FOLDER = "/mnt/c/Users/abhijain/Documents/KG4CR/data/processed/DE_newspapers"
    process_preprocessed_files(INPUT_FOLDER)