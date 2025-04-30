import pandas as pd
import os
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, XSD
import re
from datetime import datetime

# Define RDF namespaces
EX = Namespace("http://example.org/schema#")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")

# Create RDF graph
g = Graph()
g.bind("ex", EX)
g.bind("geo", GEO)

# Function to clean and create URIs
def create_uri(entity_type, value):
    """Create a clean URI by replacing spaces and handling special characters."""
    value = value.strip()
    value = re.sub(r"[^\w\s]", "", value)  # Remove special characters
    value = value.replace(" ", "_")  # Replace spaces with underscores
    return URIRef(f"http://example.org/{entity_type}/{value}")

# Function to handle multiple register types
def process_register_types(register_type_str):
    """Convert a comma-separated string into multiple URIs."""
    register_types = [t.strip() for t in register_type_str.split(",")]  # Split by commas
    return [create_uri("RegisterType", rt) for rt in register_types]

# Function to convert date format to YYYY-MM-DD
def convert_date(date_str):
    """Convert date from DD.MM.YYYY to YYYY-MM-DD format."""
    try:
        return Literal(datetime.strptime(date_str, "%d.%m.%Y").date(), datatype=XSD.date)
    except ValueError:
        return None  # Return None if the date is invalid

# Extract version number from the metadata sheet
def extract_version(file_path: str, sheet_name: str) -> str:
    try:
        df_meta = pd.read_excel(file_path, sheet_name=sheet_name)
        version_row = df_meta[df_meta.iloc[:, 0] == 'Version']
        if not version_row.empty:
            return str(version_row.iloc[0, 1])
        else:
            return "Version not found"
    except Exception as e:
        return f"Error: {str(e)}"

# Process multiple Excel files
def process_excel_files(file_paths):
    for file_path in file_paths:
        # Load Excel data
        df = pd.read_excel(file_path, skiprows=7, dtype=str)  # Skip metadata rows & read as string to avoid type issues
        df = df.iloc[:, 1:]  # Remove the first column with all NaN values
        df.columns = ["XJustizID", "RegisterCourt", "RegisterType", "State", "PLZ", "ValidUntil", "FutureCode"]
        df = df.dropna(subset=["XJustizID", "RegisterCourt", "RegisterType", "State"])  # Drop rows missing critical info

        # Extract version number from metadata sheet
        version_str = extract_version(file_path, "metadaten")
        version_uri = create_uri("Version", version_str)
        version_literal = Literal(int(version_str), datatype=XSD.integer)

        # Add the version number to the RDF graph (for version entity)
        g.add((version_uri, RDF.type, EX.Version))
        g.add((version_uri, EX.versionNumber, version_literal))  # Add versionNumber triple
        
        # Populate the RDF graph
        for _, row in df.iterrows():
            court_label = row["RegisterCourt"].strip()
            base_court_uri = create_uri("RegisterCourt", court_label)  # Stable ID
            versioned_court_uri = create_uri("RegisterCourt", f"{court_label}/_v{version_str}")  # Snapshot for version

            # Add type and reference to stable entity
            g.add((versioned_court_uri, RDF.type, EX.RegisterCourt))
            g.add((versioned_court_uri, EX.refersTo, base_court_uri))
            g.add((versioned_court_uri, RDFS.label, Literal(court_label, lang="de")))
            g.add((versioned_court_uri, EX.version, version_uri))

            # Add state location
            state_uri = create_uri("State", row["State"])
            g.add((versioned_court_uri, EX.locatedIn, state_uri))

            # XJustizID
            g.add((versioned_court_uri, EX.hasXJustizID, Literal(str(row["XJustizID"]), datatype=XSD.string)))

            # Register types (can be multiple)
            register_type_uris = process_register_types(row["RegisterType"])
            for reg_type_uri in register_type_uris:
                g.add((versioned_court_uri, EX.hasRegisterType, reg_type_uri))

            # Postal code (as string to preserve leading zeros)
            if pd.notna(row["PLZ"]):
                g.add((versioned_court_uri, EX.hasPostalCode, Literal(str(row["PLZ"]).strip(), datatype=XSD.string)))

            # validUntil date (add only if valid date exists)
            if pd.notna(row["ValidUntil"]) and row["ValidUntil"].strip():
                valid_until = convert_date(row["ValidUntil"])
                if valid_until:
                    g.add((versioned_court_uri, EX.validUntil, valid_until))
            # Optional: use a fallback like a string-typed blank or skip entirely
            # else:
                # g.add((versioned_court_uri, EX.validUntil, Literal("", datatype=XSD.string)))

            # Future code (may be empty)
            future_code = str(row["FutureCode"]) if pd.notna(row["FutureCode"]) else ""
            g.add((versioned_court_uri, EX.hasFutureCode, Literal(future_code, datatype=XSD.string)))

            # (Optional) Link base court to versioned snapshots
            g.add((base_court_uri, EX.hasSnapshot, versioned_court_uri))


# Get all Excel file paths from the given directory
def get_excel_files_from_folder(folder_path):
    # List to store file paths
    file_paths = []
    
    # Loop through files in the folder
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)
        if file_name.endswith(".xlsx") and os.path.isfile(file_path):
            file_paths.append(file_path)
    
    return file_paths

# Main logic to execute when the script is run
if __name__ == "__main__":
    # Ask the user to input the folder path containing the Excel files
    base_path = os.getcwd()    # get current working directory
    folder_path = os.path.join(base_path, "data", "raw_data")   # specify the folder path

    # Get all the Excel file paths in the specified folder
    excel_files = get_excel_files_from_folder(folder_path)

    # Ensure there are Excel files in the folder
    if not excel_files:
        print("No Excel files found in the specified folder.")
    else:
        # Process all the Excel files and append their data to the RDF graph
        process_excel_files(excel_files)

        # Save RDF data to a file
        output_ttl_file = os.path.join(base_path, "data", "processed", "with_ontology", "register_courts_combined.ttl" )   # specify the output file path
        g.serialize(output_ttl_file, format="turtle")
        print(f"RDF Data Saved: {output_ttl_file}")