import pandas as pd
import os
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, XSD
import re
from pathlib import Path
from datetime import datetime

def combine_excel_into_df(folder_path):
    """Combine multiple Excel files into a single DataFrame."""
    # Initialize list to store individual DataFrames
    all_dfs = []

    # Loop through all .xlsx files in the folder
    for file in Path(folder_path).glob("*.xlsx"):
        # Extract version number (last 2 digits before .xlsx)
        match = re.search(r"(\d{2})(?=\.xlsx$)", file.name)
        version = match.group(1) if match else None

        # Read and process the Excel file
        df = pd.read_excel(file, skiprows=7, dtype=str)
        df = df.iloc[:, 1:]  # Drop the first column
        df.columns = ["XJustizID", "RegisterCourt", "RegisterType", "State", "PLZ", "ValidUntil", "FutureCode"]

        # Add version column
        df["Version"] = version

        all_dfs.append(df)
    print(f"Found {len(all_dfs)} Excel files in {folder_path}")
    # Combine all into a single DataFrame
    combined_df = pd.concat(all_dfs, ignore_index=True)

    # Drop fully duplicated rows
    combined_df = combined_df.drop_duplicates(["XJustizID", "RegisterCourt", "RegisterType", "State", "PLZ", "ValidUntil", "FutureCode"])

    # Result
    combined_df = combined_df.reset_index(drop=True)

    return combined_df

def preprocess_combined_df(combined_df):
    """Preprocess the combined DataFrame."""
    # Ensure Version is treated as int for comparison
    combined_df["Version"] = combined_df["Version"].astype(int)

    # Separate rows based on ValidUntil presence
    with_valid = combined_df[combined_df["ValidUntil"].notna()]
    without_valid = combined_df[combined_df["ValidUntil"].isna()]

    # For each XJustizID, keep the row with max Version (ValidUntil is present)
    with_valid_dedup = with_valid.loc[with_valid.groupby("XJustizID")["Version"].idxmax()]

    # For each XJustizID, keep the row with max Version (ValidUntil is NaN)
    without_valid_dedup = without_valid.loc[without_valid.groupby("XJustizID")["Version"].idxmax()]

    # Remove XJustizID duplicates: keep only those not present in with_valid_dedup
    without_valid_dedup = without_valid_dedup[~without_valid_dedup["XJustizID"].isin(with_valid_dedup["XJustizID"])]


    # Combine both sets
    final_df = pd.concat([with_valid_dedup, without_valid_dedup], ignore_index=True)

    # Sort or reset index
    final_df = final_df.sort_values("XJustizID").reset_index(drop=True)
    
    return final_df


# Main
if __name__ == "__main__":
    base_path = os.getcwd()
    folder_path = os.path.join(base_path, "data", "raw_data")
    output_ttl_file = os.path.join(base_path, "data", "processed", "with_ontology", "register_courts_combined_v2.ttl")

    excel_files = get_excel_files_from_folder(folder_path)

    if not excel_files:
        print("No Excel files found.")
    else:
        process_excel_files(excel_files)
        g.serialize(output_ttl_file, format="turtle")
        print(f"RDF Data Saved: {output_ttl_file}")
