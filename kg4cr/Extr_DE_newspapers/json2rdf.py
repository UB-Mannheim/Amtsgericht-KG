import os
import json
import glob
import re
from rdflib import Graph, Literal, RDF, RDFS, XSD, Namespace, URIRef

def clean_uri(s):
    """Clean a string to make it URI-friendly (handles German umlauts)."""
    if not s:
        return "unknown"
    s = s.strip()
    s = (s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
           .replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue")
           .replace("ß", "ss"))
    s = s.replace(" ", "_")
    s = re.sub(r"[^\w_]", "", s)  # keep alphanumeric + underscore
    return s

def load_and_preprocess_json(folder_path):
    """Load all JSONs from folder, combine, and filter."""
    all_data = []
    json_files = glob.glob(os.path.join(folder_path, "*.json"))

    for file in json_files:
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
            all_data.extend(data)

    # Filter out entries with null Court_name or Company_name
    filtered_data = [
        entry for entry in all_data
        if entry.get("Court_name") and entry.get("Company_name")
    ]
    return filtered_data

def json_to_ttl(json_data, ttl_path="kg_companies.ttl"):
    """Convert JSON list of dicts to TTL knowledge graph."""
    # Define namespaces
    EX = Namespace("http://example.org/schema/")
    COMP = Namespace("http://example.org/company/")
    COURT = Namespace("http://example.org/court/")

    # Initialize RDF Graph
    g = Graph()
    g.bind("ex", EX)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)

    # --- Ontology definition ---
    g.add((EX.Company, RDF.type, RDFS.Class))
    g.add((EX.Court, RDF.type, RDFS.Class))

    g.add((EX.companyName, RDF.type, RDF.Property))
    g.add((EX.companyName, RDFS.domain, EX.Company))
    g.add((EX.companyName, RDFS.range, XSD.string))

    g.add((EX.courtName, RDF.type, RDF.Property))
    g.add((EX.courtName, RDFS.domain, EX.Court))
    g.add((EX.courtName, RDFS.range, XSD.string))

    g.add((EX.registeredAt, RDF.type, RDF.Property))
    g.add((EX.registeredAt, RDFS.domain, EX.Company))
    g.add((EX.registeredAt, RDFS.range, EX.Court))

    g.add((EX.registrationCode, RDF.type, RDF.Property))
    g.add((EX.registrationCode, RDFS.domain, EX.Company))
    g.add((EX.registrationCode, RDFS.range, XSD.string))

    g.add((EX.registrationYear, RDF.type, RDF.Property))
    g.add((EX.registrationYear, RDFS.domain, EX.Company))
    g.add((EX.registrationYear, RDFS.range, XSD.gYear))

    g.add((EX.articleDate, RDF.type, RDF.Property))
    g.add((EX.articleDate, RDFS.domain, EX.Company))
    g.add((EX.articleDate, RDFS.range, XSD.string))
    # (could refine with xsd:date if parsed properly)

    # --- Instance data ---
    for idx, entry in enumerate(json_data):
        company_uri = URIRef(COMP[clean_uri(entry.get("Company_name", str(idx)))])
        court_uri = URIRef(COURT[clean_uri(entry.get("Court_name", str(idx)))])

        # Company triple
        g.add((company_uri, RDF.type, EX.Company))
        g.add((company_uri, EX.companyName, Literal(entry.get("Company_name"))))

        # Court triple
        g.add((court_uri, RDF.type, EX.Court))
        g.add((court_uri, EX.courtName, Literal(entry.get("Court_name"))))

        # Link company → court
        g.add((company_uri, EX.registeredAt, court_uri))

        # Registration Code
        if entry.get("Registration_Code"):
            g.add((company_uri, EX.registrationCode, Literal(entry["Registration_Code"])))

        # Registration Year
        if entry.get("Registration_year"):
            g.add((company_uri, EX.registrationYear, Literal(entry["Registration_year"], datatype=XSD.gYear)))

        # Article Date
        if entry.get("Date_of_article"):
            g.add((company_uri, EX.articleDate, Literal(entry["Date_of_article"])))

    # Save once, after loop
    with open(ttl_path, "wb") as f:
        f.write(g.serialize(format="turtle").encode('utf-8'))

if __name__ == "__main__":
    folder_path = "/mnt/c/Users/abhijain/Documents/KG4CR/data/processed/json2rdf"
    ttl_path = "/mnt/c/Users/abhijain/Documents/KG4CR/data/processed/json2rdf/DE_N_ontology.ttl"

    combined_data = load_and_preprocess_json(folder_path)
    json_to_ttl(combined_data, ttl_path)
