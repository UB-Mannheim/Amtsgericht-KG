import json
import re
from difflib import SequenceMatcher
from pathlib import Path

def clean_string(s):
    """Remove spaces, hyphens, dots, commas, and special ⸗ for comparison."""
    if s is None:
        return ""
    s = str(s).lower()
    s = re.sub(r'[\s\-\.,⸗]', '', s)
    return s

def similarity(a, b):
    """Return similarity between two strings as a float between 0 and 1."""
    return SequenceMatcher(None, clean_string(a), clean_string(b)).ratio()

def find_best_match(gt_item, parsed_list, used_indices, threshold=0.5):
    """
    Find the parsed record with highest similarity for Court_name + Company_name.
    Return None if no record crosses the threshold.
    """
    best_score = -1
    best_idx = None
    for idx, parsed_item in enumerate(parsed_list):
        if idx in used_indices:
            continue
        score = similarity(gt_item.get('Court_name'), parsed_item.get('Court_name')) + \
                similarity(gt_item.get('Company_name'), parsed_item.get('Company_name'))
        if score > best_score:
            best_score = score
            best_idx = idx
    # Optional: consider it a match only if score passes threshold
    if best_score < threshold:
        return None
    return best_idx

def compare_json_weighted(gt_list, parsed_list):
    obtained_score = 0
    max_score = 0
    unmatched_binary_records = []
    used_indices = set()

    # Weights for fields
    field_weights = {
        'Court_name': 2,
        'Date_of_article': 1,
        'Company_name': 2,
        'Registration_Code': 2,
        'Registration_year': 2
    }
    max_total_weight = sum(field_weights.values())

    for idx, gt_item in enumerate(gt_list, start=1):
        max_score += max_total_weight  # Each ground_truth record contributes max possible weight

        best_idx = find_best_match(gt_item, parsed_list, used_indices)
        if best_idx is None:
            # No match found, score for this record is 0
            continue

        parsed_item = parsed_list[best_idx]
        used_indices.add(best_idx)

        item_score = 0
        binary_mismatch = {}

        for key, weight in field_weights.items():
            if key in ['Registration_Code', 'Registration_year']:
                # Binary comparison
                field_similarity = 1 if clean_string(gt_item.get(key)) == clean_string(parsed_item.get(key)) else 0
                if field_similarity == 0:
                    binary_mismatch[key] = {
                        'Ground_Truth': gt_item.get(key),
                        'Parsed_Result': parsed_item.get(key)
                    }
            else:
                # Fuzzy similarity
                field_similarity = similarity(gt_item.get(key), parsed_item.get(key))

            item_score += field_similarity * weight

        obtained_score += item_score

        if binary_mismatch:
            binary_mismatch['Record'] = idx
            unmatched_binary_records.append(binary_mismatch)

    overall_weighted_similarity = obtained_score / max_score if max_score > 0 else 0
    return round(overall_weighted_similarity, 2), unmatched_binary_records

def main(gt_path, parsed_path):
    with open(gt_path, 'r', encoding='utf-8') as f:
        ground_truth = json.load(f)

    with open(parsed_path, 'r', encoding='utf-8') as f:
        parsed_result = json.load(f)
    
    overall_score, unmatched_binary_records = compare_json_weighted(ground_truth, parsed_result)
    
    print(f"Overall weighted similarity score: {overall_score:.2f}\n")
    print("Records with mismatched binary fields (Registration_Code or Registration_year):")
    for record in unmatched_binary_records:
        print(record)


if __name__ == "__main__":
    # Example relative paths
    gt_path = "../KG4CR/data/processed/DE_newspapers_subset/GT_Reichsanzeiger_06_09_1927.json"
    parsed_path = "../KG4CR/data/processed/DE_newspapers_subset/Reichsanzeiger_06_09_1927.json"
    
    main(gt_path, parsed_path)
