import os
import json
import glob
import re
from rdflib import Graph, Literal, RDF, RDFS, Namespace, URIRef

def clean_uri(s):
    """Clean a string to make it URI-friendly (handles German umlauts)."""
    s = s.strip()
    # Replace German umlauts and ß with ASCII-friendly versions
    s = (s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
           .replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue")
           .replace("ß", "ss"))
    s = s.replace(" ", "_")
    s = re.sub(r"[^\w_]", "", s)  # remove all non-word characters except underscore
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

def json_to_ttl(data, ttl_path="kg_companies.ttl"):
    """Convert JSON to TTL knowledge graph."""
    EX = Namespace("http://example.org/schema#")
    COURT = Namespace("http://example.org/RegisterCourt/")
    COMP = Namespace("http://example.org/Company/")

    g = Graph()
    g.bind("ex", EX)
    g.bind("court", COURT)
    g.bind("comp", COMP)

    # Define Classes
    g.add((EX.RegisterCourt, RDF.type, RDFS.Class))
    g.add((EX.RegisterCourt, RDFS.label, Literal("Register Court", lang="en")))

    g.add((EX.Company, RDF.type, RDFS.Class))
    g.add((EX.Company, RDFS.label, Literal("Company", lang="en")))

    # Define Properties
    g.add((EX.hasCompany, RDF.type, RDF.Property))
    g.add((EX.hasCompany, RDFS.domain, EX.RegisterCourt))
    g.add((EX.hasCompany, RDFS.range, EX.Company))
    g.add((EX.hasCompany, RDFS.label, Literal("has Company", lang="en")))

    g.add((EX.dateOfArticle, RDF.type, RDF.Property))
    g.add((EX.dateOfArticle, RDFS.domain, EX.Company))
    g.add((EX.dateOfArticle, RDFS.range, URIRef("http://www.w3.org/2001/XMLSchema#string")))

    g.add((EX.registrationCode, RDF.type, RDF.Property))
    g.add((EX.registrationCode, RDFS.domain, EX.Company))
    g.add((EX.registrationCode, RDFS.range, URIRef("http://www.w3.org/2001/XMLSchema#string")))

    g.add((EX.registrationYear, RDF.type, RDF.Property))
    g.add((EX.registrationYear, RDFS.domain, EX.Company))
    g.add((EX.registrationYear, RDFS.range, URIRef("http://www.w3.org/2001/XMLSchema#gYear")))

    # Add instances
    for i, entry in enumerate(data):
        # Court node
        court_uri = COURT[clean_uri(entry["Court_name"])]
        g.add((court_uri, RDF.type, EX.RegisterCourt))
        g.add((court_uri, RDFS.label, Literal(entry["Court_name"], lang="de")))

        # Company node
        comp_uri = COMP[f"company{i+1}"]
        g.add((comp_uri, RDF.type, EX.Company))
        g.add((comp_uri, RDFS.label, Literal(entry["Company_name"], lang="de")))

        # Link court -> company
        g.add((court_uri, EX.hasCompany, comp_uri))

        # Company properties
        if entry.get("Date_of_article"):
            g.add((comp_uri, EX.dateOfArticle, Literal(entry["Date_of_article"], datatype=URIRef("http://www.w3.org/2001/XMLSchema#string"))))
        if entry.get("Registration_Code"):
            g.add((comp_uri, EX.registrationCode, Literal(entry["Registration_Code"], datatype=URIRef("http://www.w3.org/2001/XMLSchema#string"))))
        if entry.get("Registration_year"):
            g.add((comp_uri, EX.registrationYear, Literal(entry["Registration_year"], datatype=URIRef("http://www.w3.org/2001/XMLSchema#gYear"))))

    # Save TTL
    g.serialize(ttl_path, format="turtle")
    print(f"✅ TTL file created: {ttl_path}")
    print(f"📊 Total courts: {len(set(clean_uri(e['Court_name']) for e in data))}, Total companies: {len(data)}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert JSON folder to TTL Knowledge Graph")
    parser.add_argument("folder_path", type=str, help="Path to folder containing JSON files")
    parser.add_argument("--ttl_path", type=str, default="kg_companies.ttl", help="Output TTL file path")

    args = parser.parse_args()

    combined_data = load_and_preprocess_json(args.folder_path)
    json_to_ttl(combined_data, args.ttl_path)
