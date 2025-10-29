import os
import json
import glob
import re
from rdflib import Graph, Literal, RDF, RDFS, XSD, Namespace, URIRef


def safe_literal(value, datatype=None):
    """Safely create RDF Literals, handling invalid gYear values and other formats."""
    if value in (None, "", "unbekannt", "unknown", "?", "-", "N/A"):
        return None

    if datatype == XSD.gYear:
        try:
            year_str = str(value).strip().replace(".", "")
            if year_str.isdigit() and 0 < int(year_str) < 9999:
                return Literal(year_str, datatype=XSD.gYear)
            else:
                return Literal(str(value))
        except Exception:
            return Literal(str(value))

    return Literal(value, datatype=datatype) if datatype else Literal(value)


def clean_uri(s):
    """Clean a string to make it URI-safe (handles German umlauts)."""
    if not s:
        return "unknown"
    s = s.strip()
    s = (
        s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
        .replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue")
        .replace("ß", "ss")
    )
    s = s.replace(" ", "_")
    s = re.sub(r"[^\w_]", "", s)
    return s


def load_and_preprocess_json(path):
    """Load JSONs from a folder or file, combine, and filter."""
    all_data = []

    if os.path.isdir(path):
        json_files = glob.glob(os.path.join(path, "*.json"))
    else:
        json_files = [path] if path.lower().endswith(".json") else []

    for file in json_files:
        with open(file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                # Add file_name field to each entry
                for d in data:
                    d["fileName"] = os.path.basename(file)
                all_data.extend(data)
            except Exception as e:
                print(f"⚠️ Skipping {file}: {e}")

    filtered_data = [
        entry for entry in all_data
        if entry.get("Court_name") and entry.get("Company_name")
    ]
    return filtered_data


def json_to_ttl(json_data, ttl_path):
    """Convert JSON list of dicts to RDF/Turtle format."""
    EX = Namespace("http://example.org/schema/")
    COMP = Namespace("http://example.org/company/")
    COURT = Namespace("http://example.org/court/")

    g = Graph()
    g.bind("ex", EX)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)

    # Force RDFLib to keep prefix declarations
    g.add((RDF.type, RDFS.label, Literal("keep_prefix")))

    # Define ontology schema
    g.add((EX.Company, RDF.type, RDFS.Class))
    g.add((EX.Court, RDF.type, RDFS.Class))
    g.add((EX.companyName, RDF.type, RDF.Property))
    g.add((EX.courtName, RDF.type, RDF.Property))
    g.add((EX.registeredAt, RDF.type, RDF.Property))
    g.add((EX.registrationCode, RDF.type, RDF.Property))
    g.add((EX.registrationYear, RDF.type, RDF.Property))
    g.add((EX.articleDate, RDF.type, RDF.Property))
    g.add((EX.fileName, RDF.type, RDF.Property))

    for idx, entry in enumerate(json_data):
        company_uri = URIRef(f"http://example.org/company/{clean_uri(entry.get('Company_name', str(idx)))}")
        court_uri = URIRef(f"http://example.org/court/{clean_uri(entry.get('Court_name', str(idx)))}")

        g.add((company_uri, RDF.type, EX.Company))
        g.add((court_uri, RDF.type, EX.Court))
        g.add((company_uri, EX.companyName, Literal(entry.get("Company_name"))))
        g.add((court_uri, EX.courtName, Literal(entry.get("Court_name"))))
        g.add((company_uri, EX.registeredAt, court_uri))

        if entry.get("Registration_Code"):
            g.add((company_uri, EX.registrationCode, Literal(entry["Registration_Code"])))

        if entry.get("Registration_year"):
            year_literal = safe_literal(entry["Registration_year"], datatype=XSD.gYear)
            if year_literal:
                g.add((company_uri, EX.registrationYear, year_literal))

        if entry.get("Date_of_article"):
            g.add((company_uri, EX.articleDate, Literal(entry["Date_of_article"])))

        if entry.get("fileName"):
            g.add((company_uri, EX.fileName, Literal(entry["fileName"])))

    # Serialize with full URIs (not compacted prefixes)
    ttl_data = g.serialize(format="turtle")
    # Remove dummy prefix-keeping triple
    ttl_data = ttl_data.replace('rdf:type rdfs:label "keep_prefix" .', "").strip()

    with open(ttl_path, "w", encoding="utf-8") as f:
        f.write(ttl_data)

    print(f"✅ RDF graph successfully generated at: {ttl_path}")

if __name__ == "__main__":
    # Go 3 levels up (from kg4cr/Extr_DE_newspapers/json2rdf.py → KG4CR/)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Define input/output folders
    folder_path = os.path.join(BASE_DIR, "data", "processed", "DE_newspapers_1920_45_processed")
    # Define TTL output path inside a 'Qlever' subfolder
    qlever_folder = os.path.join(folder_path, "Qlever")
    ttl_path = os.path.join(qlever_folder, "DE_1920_45_comb_ontology.ttl")

    # Ensure directory exists
    os.makedirs(qlever_folder, exist_ok=True)

    # Collect all JSON file paths from all subfolders
    all_json_files = []
    for root, _, files in os.walk(folder_path):
        for f in files:
            if f.lower().endswith(".json"):
                all_json_files.append(os.path.join(root, f))

    print(f"🔍 Found {len(all_json_files)} JSON files to process across subfolders.")

    # Load and preprocess data from all JSONs
    combined_data = []
    for json_file in all_json_files:
        data = load_and_preprocess_json(json_file)  # assuming this takes a file path now
        combined_data.extend(data)
    print(f"ℹ️  Combined and filtered to {len(combined_data)} valid entries.")
    # Convert to RDF/Turtle
    json_to_ttl(combined_data, ttl_path)

    print(f"✅ RDF graph successfully generated at: {ttl_path}")
