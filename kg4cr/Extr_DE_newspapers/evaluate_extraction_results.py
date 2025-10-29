import json
import re
import sys

# --- Scoring Weights ---
weights = {
    "Court_name": ("regex", 2),
    "Date_of_article": ("regex", 1),
    "Company_name": ("regex", 2),
    "Registration_Code": ("binary", 2),
    "Registration_year": ("binary", 2)
}

# --- Matching Functions ---
def regex_match(a, b):
    if not a or not b:
        return 0
    return 1 if re.search(re.escape(b), a, re.IGNORECASE) or re.search(re.escape(a), b, re.IGNORECASE) else 0

def binary_match(a, b):
    return 1 if a and b and str(a).strip().lower() == str(b).strip().lower() else 0

def compute_weighted_similarity(gt_item, parsed_item):
    score = 0
    for key, (match_type, weight) in weights.items():
        if match_type == "regex":
            score += regex_match(gt_item.get(key), parsed_item.get(key)) * weight
        else:
            score += binary_match(gt_item.get(key), parsed_item.get(key)) * weight
    return score

# --- Main Comparison ---
def compare_jsons(gt_path, parsed_path):
    with open(gt_path, 'r', encoding='utf-8') as f:
        gt_data = json.load(f)
    with open(parsed_path, 'r', encoding='utf-8') as f:
        parsed_data = json.load(f)

    ideal_weighted_similarity_score = sum(weight for _, weight in weights.values())
    max_score = len(gt_data) * ideal_weighted_similarity_score
    obtained_score = 0
    matched_indices = set()
    mismatched_reg_codes = []

    print("Detailed Comparison Results:\n")

    for i, gt_item in enumerate(gt_data):
        best_score = 0
        best_match_index = None

        # find the closest parsed record for this ground truth
        for j, parsed_item in enumerate(parsed_data):
            if j in matched_indices:
                continue
            score = compute_weighted_similarity(gt_item, parsed_item)
            if score > best_score:
                best_score = score
                best_match_index = j

        # store the match and compute totals
        if best_match_index is not None:
            matched_indices.add(best_match_index)
            parsed_item = parsed_data[best_match_index]
        else:
            parsed_item = {}

        obtained_score += best_score
        print(f"GT Record {i+1}: best match → Parsed Record {best_match_index+1 if best_match_index is not None else 'None'} "
              f"with weighted_similarity_score = {best_score} / {ideal_weighted_similarity_score}")

        # --- Check for Registration_Code mismatch ---
        gt_code = gt_item.get("Registration_Code")
        parsed_code = parsed_item.get("Registration_Code") if parsed_item else None

        # Only flag if they differ (not both None or equal)
        if (gt_code or parsed_code) and (str(gt_code).strip().lower() != str(parsed_code).strip().lower()):
            mismatched_reg_codes.append((i + 1, gt_code, parsed_code, gt_item, parsed_item))
    
    # --- Summary ---
    overall_similarity = obtained_score / max_score if max_score else 0

    print("\n--- Registration_Code Mismatches ---")
    if not mismatched_reg_codes:
        print("✅ No mismatches in Registration_Code detected.")
    else:
        for rec_no, gt_code, parsed_code, gt_item, parsed_item in mismatched_reg_codes:
            print(f"\n⚠️  GT Record {rec_no} has Registration_Code mismatch:")
            print(f"   → GT Company: {gt_item.get('Company_name')}")
            print(f"     GT Court: {gt_item.get('Court_name')}")
            print(f"     GT Reg Code: {gt_code}")
            print(f"   → Parsed Company: {parsed_item.get('Company_name')}")
            print(f"     Parsed Court: {parsed_item.get('Court_name')}")
            print(f"     Parsed Reg Code: {parsed_code}")

    print("\n--- Summary ---")
    print(f"Max Score: {max_score}")
    print(f"Obtained Score: {obtained_score}")
    print(f"Overall Similarity Score: {overall_similarity:.4f}")
    print(f"Total Registration_Code mismatches: {len(mismatched_reg_codes)}")

# --- Run from command line ---
if __name__ == "__main__":
    parsed_file_path = r"C:\Users\abhijain\Documents\KG4CR\data\processed\test_json_processed\Reichsanzeiger_06_09_1927.json"
    gt_file_path = r"C:\Users\abhijain\Documents\KG4CR\data\processed\DE_newspapers_subset\GT_Reichsanzeiger_06_09_1927.json"
    compare_jsons(gt_file_path, parsed_file_path)

