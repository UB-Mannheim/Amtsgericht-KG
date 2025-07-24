import os
from glob import glob
import re
import unicodedata
import logging
from spellchecker import SpellChecker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

OCR_CORRECTIONS = {
    # OCR misreads
    r'\bJentral': 'Zentral',
    r'\bbandels': 'handels',
    r'\bGexicht': 'Gericht',
    r'\bVeraleich': 'Vergleich',
    r'\bBeschlus[s|z]': 'Beschluss',
    r'\bAnitsgericht': 'Amtsgericht',
    r'\bZwanasvergleich': 'Zwangsvergleich',
    r'\bMninm': 'Main',
    r'\bSchlußteymins?': 'Schlusstermins?',
    r'\bCle ve': 'Cleve',
    r'\bDęessan': 'Dessau',
    r'\bMolch⸗rundstraße': 'Molchgrundstraße',
    r'\bAltong': 'Altona',
    r'\bHerrmann': 'Hermann',
    r'\bKonkursverfahren\b': 'Konkursverfahren',
}

HISTORICAL_SPELLING_CORRECTIONS = {
    r'\bSchluß': 'Schluss',
    r'\bThür\.': 'Thüring.',
    r'\bKaufmanns': 'Kaufmann',
    r'\bVermögen des .*? in\b': lambda m: f"Vermögen von {m.group(0).split(' ')[2]}",  # Optional: simplify
}

def normalize_unicode(text):
    normalized = unicodedata.normalize("NFKC", text)
    if text != normalized:
        logging.info("Unicode normalization applied.")
    else:
        logging.info("Text was already normalized.")
    return normalized

def apply_corrections(text, corrections, description=""):
    for pattern, replacement in corrections.items():
        if isinstance(replacement, str):
            matches = re.findall(pattern, text)
            if matches:
                logging.info(f"[{description}] Found {len(matches)} occurrence(s) of pattern: {pattern}")
            text = re.sub(pattern, replacement, text)
        elif callable(replacement):  # dynamic replacements
            text = re.sub(pattern, replacement, text)
    return text

def fix_hyphenation(text):
    # Join hyphenated line breaks
    pattern = re.compile(r'([a-zäöüß])[\-\u2010-\u2015\u2E3A-\u2E40⸗]?\s*\n\s*([a-zäöüß])', re.IGNORECASE)
    text, subs_made = pattern.subn(r'\1\2', text)
    if subs_made:
        logging.info(f"Hyphenation fixed: {subs_made} cases.")

    # Merge soft line breaks that interrupt sentences
    text = re.sub(r'(?<![.:\-\n])\n(?![\nA-ZÄÖÜ])', ' ', text)

    return text

def fix_umlauts_and_eszett(text):
    replacements = [
        (r'\bä\b', 'ä'), (r'\bö\b', 'ö'), (r'\bü\b', 'ü'),
        (r'ä', 'ä'), (r'ö', 'ö'), (r'ü', 'ü'),
        (r'Ä', 'Ä'), (r'Ö', 'Ö'), (r'Ü', 'Ü'),
        (r'ß', 'ß')  # Keep ß unchanged
    ]
    total_replacements = 0
    for pat, repl in replacements:
        count = len(re.findall(pat, text))
        if count:
            logging.info(f"Replaced {count} occurrence(s) of '{pat}' with '{repl}'.")
            text = re.sub(pat, repl, text)
            total_replacements += count
    if total_replacements == 0:
        logging.info("No umlaut/ß replacements necessary.")
    return text

def remove_noise(text):
    original_length = len(text)
    noise_patterns = [
        r'\d{4}\s*/\s*\d+\s*p\.\s*\d+',   # Page tags
        r'scan diff',                    # Scan diff tag
        r'Zregistereintrag',             # Common OCR noise
        r'[⸗*]+',                        # Misc punctuation
        r'–{2,}',                        # Long dashes
        r'\x0c|\x0b|\t',                 # Form feeds, tabs
        r'\s{2,}',                       # Extra spaces
    ]
    for pat in noise_patterns:
        text = re.sub(pat, '', text, flags=re.IGNORECASE)
    text = text.strip()
    new_length = len(text)
    if new_length < original_length:
        logging.info(f"Noise removed. Reduced by {original_length - new_length} characters.")
    else:
        logging.info("No noise removed.")
    return text

def spell_correct(text, spellchecker):
    words = text.split()
    corrected_words = []
    corrections = []

    for word in words:
        if len(word) <= 2 or word.isupper():
            corrected_words.append(word)
            continue

        if word.lower() in spellchecker:
            corrected_words.append(word)
        else:
            suggestions = spellchecker.candidates(word) or set()
            best_guess = next(iter(suggestions), word)
            if best_guess != word:
                corrections.append((word, best_guess))
            corrected_words.append(best_guess)

    if corrections:
        logging.info(f"{len(corrections)} words corrected.")
        for wrong, correct in corrections[:10]:
            logging.info(f" - '{wrong}' → '{correct}'")
        if len(corrections) > 10:
            logging.info(f"...and {len(corrections) - 10} more.")
    else:
        logging.info("No spelling corrections made.")

    return ' '.join(corrected_words)


def batch_process_newspapers(folder_path):
    files = glob(os.path.join(folder_path, "**", "*.txt"), recursive=True)

    logging.info(f"Found {len(files)} text files to process.")

    spell = SpellChecker(language='de')

    for filepath in files:
        filename = os.path.basename(filepath)
        logging.info(f"\nProcessing file: {filename}")

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                raw_text = f.read()
        except Exception as e:
            logging.error(f"Failed to read {filename}: {e}")
            continue

        # Apply processing pipeline
        text = normalize_unicode(raw_text)
        text = fix_hyphenation(text)
        text = fix_umlauts_and_eszett(text)
        text = remove_noise(text)
        text = spell_correct(text, spell)

        # Apply OCR and spelling corrections
        text = apply_corrections(text, OCR_CORRECTIONS, "OCR")
        text = apply_corrections(text, HISTORICAL_SPELLING_CORRECTIONS, "Spelling")

        # Save output
        new_filename = os.path.splitext(filename)[0] + "_processed.txt"
        output_path = os.path.join(folder_path, new_filename)
        try:
            with open(output_path, "w", encoding="utf-8") as out:
                out.write(text)
            logging.info(f"Saved cleaned text to: {new_filename}")
        except Exception as e:
            logging.error(f"Could not save {new_filename}: {e}")

# Folder with raw OCR .txt files
INPUT_FOLDER = "/mnt/c/Users/abhijain/Documents/KG4CR/data/processed/DE_newspapers"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    batch_process_newspapers(INPUT_FOLDER)
