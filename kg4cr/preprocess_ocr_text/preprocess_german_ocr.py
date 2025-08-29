import os
from glob import glob
import re
import unicodedata
import logging
from symspellpy.symspellpy import SymSpell, Verbosity
from concurrent.futures import ProcessPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# Path to frequency dictionary
GERMAN_DICT_PATH = r"C:\Users\Abhinandan_Jain\Documents\Uni_Mannheim\KG4CR\de-100k.txt"

# Folder paths
INPUT_FOLDER = r"C:\Users\Abhinandan_Jain\Documents\Uni_Mannheim\KG4CR\data\raw_data\DE_newspapers"
OUTPUT_FOLDER = r"C:\Users\Abhinandan_Jain\Documents\Uni_Mannheim\KG4CR\data\processed\DE_newspapers"

OCR_CORRECTIONS = {
    r'\bJentral': 'Zentral',
    r'\bbandels': 'handels',
    r'\bGexicht': 'Gericht',
    r'\bVeraleich': 'Vergleich',
    r'\bBeschlus[s|z]': 'Beschluss',
    r'\bAnitsgericht': 'Amtsgericht',
    r'\bZwanasvergleich': 'Zwangsvergleich',
    r'\bMninm': 'Main',
    r'\bSchlu\u00dfteymins?': 'Schlusstermins?',
    r'\bCle ve': 'Cleve',
    r'\bD\u0119essan': 'Dessau',
    r'\bMolch\u2e17rundstra\u00dfe': 'Molchgrundstraße',
    r'\bAltong': 'Altona',
    r'\bHerrmann': 'Hermann',
    r'\bKonkursverfahren\b': 'Konkursverfahren',
}

HISTORICAL_SPELLING_CORRECTIONS = {
    r'\bSchlu\u00df': 'Schluss',
    r'\bTh\u00fcr\.': 'Thüring.',
    r'\bKaufmanns': 'Kaufmann',
}

def init_symspell():
    sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
    sym_spell.load_dictionary(GERMAN_DICT_PATH, term_index=0, count_index=1)
    return sym_spell

def normalize_unicode(text):
    return unicodedata.normalize("NFKC", text)

def apply_corrections(text, corrections):
    for pattern, replacement in corrections.items():
        text = re.sub(pattern, replacement if isinstance(replacement, str) else replacement(text), text)
    return text

def fix_hyphenation(text):
    pattern = re.compile(r'([a-zäöüß])[-\u2010-\u2015\u2E3A-\u2E40⸗]?\s*\n\s*([a-zäöüß])', re.IGNORECASE)
    text = pattern.sub(r'\1\2', text)
    text = re.sub(r'(?<![.:\-\n])\n(?![\nA-ZÄÖÜ])', ' ', text)
    return text

def fix_umlauts_and_eszett(text):
    replacements = [
        (r'\bä\b', 'ä'), (r'\bö\b', 'ö'), (r'\bü\b', 'ü'),
        (r'ä', 'ä'), (r'ö', 'ö'), (r'ü', 'ü'),
        (r'Ä', 'Ä'), (r'Ö', 'Ö'), (r'Ü', 'Ü'),
        (r'ß', 'ß')
    ]
    for pat, repl in replacements:
        text = re.sub(pat, repl, text)
    return text

def remove_noise(text):
    noise_patterns = [
        r'\d{4}\s*/\s*\d+\s*p\.\s*\d+',
        r'scan diff',
        r'Zregistereintrag',
        r'[⸗*]+',
        r'–{2,}',
        r'\x0c|\x0b|\t',
        r'\s{2,}'
    ]
    for pat in noise_patterns:
        text = re.sub(pat, '', text, flags=re.IGNORECASE)
    return text.strip()

def spell_correct_symspell(text, sym_spell):
    corrected_text = []
    for word in text.split():
        suggestions = sym_spell.lookup(word, Verbosity.CLOSEST, max_edit_distance=2)
        if suggestions:
            corrected_text.append(suggestions[0].term)
        else:
            corrected_text.append(word)
    return ' '.join(corrected_text)

def process_file(filepath):
    sym_spell = init_symspell()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            raw_text = f.read()
    except Exception as e:
        logging.error(f"Failed to read {filepath}: {e}")
        return

    text = normalize_unicode(raw_text)
    text = fix_hyphenation(text)
    text = fix_umlauts_and_eszett(text)
    text = remove_noise(text)
    text = spell_correct_symspell(text, sym_spell)
    text = apply_corrections(text, OCR_CORRECTIONS)
    text = apply_corrections(text, HISTORICAL_SPELLING_CORRECTIONS)

    base_name = os.path.splitext(os.path.basename(filepath))[0]
    new_filename = base_name + "_processed.txt"
    output_path = os.path.join(OUTPUT_FOLDER, new_filename)

    try:
        with open(output_path, "w", encoding="utf-8") as out:
            out.write(text)
        logging.info(f"Saved cleaned text to: {output_path}")
    except Exception as e:
        logging.error(f"Could not save {output_path}: {e}")

def batch_process_newspapers():
    files = glob(os.path.join(INPUT_FOLDER, "*.txt"))
    logging.info(f"Found {len(files)} text files to process.")
    with ProcessPoolExecutor() as executor:
        executor.map(process_file, files)

if __name__ == "__main__":
    batch_process_newspapers()