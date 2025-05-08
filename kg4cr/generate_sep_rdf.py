import pandas as pd
import os
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, XSD
import re
from datetime import datetime

# Define RDF namespaces
EX = Namespace("http://example.org/schema#")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")

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

# Process a single Excel file and create a TTL file for it
def process_excel_file(file_path):
    # Load Excel data
    df = pd.read_excel(file_path, skiprows=7, dtype=str)  # Skip metadata rows & read as string to avoid type issues

    # Remove the first column with all NaN values
    df = df.iloc[:, 1:]
    df.columns = ["XJustizID", "RegisterCourt", "RegisterType", "State", "PLZ", "ValidUntil", "FutureCode"]

    # Remove empty rows
    df = df.dropna(subset=["XJustizID", "RegisterCourt", "RegisterType", "State"])

    # Extract version number from the metadata sheet
    version = extract_version(file_path, "metadaten")
    version_literal = Literal(version, datatype=XSD.integer)

    # Create RDF graph for this file
    g = Graph()
    g.bind("ex", EX)
    g.bind("geo", GEO)

    # Populate the RDF graph with data
    for _, row in df.iterrows():
        court_uri = create_uri("RegisterCourt", row["RegisterCourt"])
        state_uri = create_uri("State", row["State"])

        g.add((court_uri, RDF.type, EX.RegisterCourt))
        g.add((court_uri, RDFS.label, Literal(row["RegisterCourt"], lang="de")))
        g.add((court_uri, EX.locatedIn, state_uri))
        g.add((court_uri, EX.version, version_literal))  # Add version property to each entity

        # Add XJustizID (even if empty)
        g.add((court_uri, EX.hasXJustizID, Literal(str(row["XJustizID"]), datatype=XSD.string)))

        # Handle multiple register types
        register_type_uris = process_register_types(row["RegisterType"])
        for reg_type_uri in register_type_uris:
            g.add((court_uri, EX.hasRegisterType, reg_type_uri))

        # Convert postal code if present
        if pd.notna(row["PLZ"]):
            g.add((court_uri, EX.hasPostalCode, Literal(str(row["PLZ"]).strip(), datatype=XSD.string)))  # stored as string as conversion to INT might lead to omission of initial zeros (e.g., 01234 -> 1234))

        # Convert and add validUntil date
        if pd.notna(row["ValidUntil"]):
            valid_until = convert_date(row["ValidUntil"])
            if valid_until:
                g.add((court_uri, EX.validUntil, valid_until))

        # Add Future Code (even if empty)
        future_code = str(row["FutureCode"]) if pd.notna(row["FutureCode"]) else ""
        g.add((court_uri, EX.hasFutureCode, Literal(future_code, datatype=XSD.string)))

    # Generate the TTL filename with version suffix
    version_suffix = version.replace(" ", "_").replace(":", "_")  # Clean the version string for filenames
    base_path = os.getcwd()  # get current working directory
    output_ttl_file = os.path.join(base_path, "data", "processed", f"register_courts_{version_suffix}.ttl")

    # Save RDF data to a TTL file
    g.serialize(output_ttl_file, format="turtle")
    print(f"RDF Data Saved: {output_ttl_file}")

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
    # Specify the folder path
    base_path = os.getcwd()  # get current working directory
    folder_path = os.path.join(base_path, "data", "raw_data")  # specify the folder path

    # Get all the Excel file paths in the specified folder
    excel_files = get_excel_files_from_folder(folder_path)

    # Ensure there are Excel files in the folder
    if not excel_files:
        print("No Excel files found in the specified folder.")
    else:
        # Process all the Excel files individually
        for file_path in excel_files:
            process_excel_file(file_path)
