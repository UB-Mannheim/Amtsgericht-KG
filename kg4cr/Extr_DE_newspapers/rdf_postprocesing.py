import os
import re
from rdflib import Graph, Namespace, Literal, RDF

def normalize_text(text: str) -> str:
    """
    Normalize and clean German text with encoding corruptions and OCR artifacts.
    Converts umlauts and ß to ASCII equivalents (ue, oe, ae, ss).
    Example: München -> Muenchen, GeÅ¿ellÅ¿chaft -> Gesellschaft -> Gesellschaft -> Gesellschaft -> Gesellschaft
    """

    if not text:
        return text

    # 1. Try to fix double-encoding (MÃ¼nchen → München → Muenchen)
    try:
        text = text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass

    # 2. Replace known corruptions
    replacements = {
        "Ã¼": "ü", "Ãœ": "Ü",
        "Ã¶": "ö", "Ã–": "Ö",
        "Ã¤": "ä", "Ã„": "Ä",
        "ÃŸ": "ß", "Å¿": "ß",
        "Ã©": "é",
        "â€“": "-", "â€”": "-", "â€": '"', "â€œ": '"',
        "Ã ": "à", "Ã¡": "á", "Ã²": "ò", "Ã³": "ó",
        "Â": "",
    }

    for k, v in replacements.items():
        text = text.replace(k, v)

    # 3. Fix long-s and OCR artifacts
    text = text.replace("ſ", "s")
    text = text.replace("Å¿", "ß")

    # 4. Fix specific corrupted common terms
    text = text.replace("GeÅ¿ellÅ¿chaft", "Gesellschaft")
    text = text.replace("AktiengeÅ¿ellÅ¿chaft", "Aktiengesellschaft")

    # 5. Replace German umlauts with ASCII equivalents
    umlaut_map = {
        "ä": "ae", "ö": "oe", "ü": "ue",
        "Ä": "Ae", "Ö": "Oe", "Ü": "Ue",
        "ß": "ss"
    }
    for k, v in umlaut_map.items():
        text = text.replace(k, v)

    # 6. Remove stray or non-printable chars
    text = re.sub(r"[~`^¨´]", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text.strip()


def postprocess_ttl(ttl_path, output_path):
    """
    Postprocess the extracted TTL file by filtering, cleaning entities,
    and correcting encoding/ocr artifacts (with ASCII umlaut normalization).
    """

    EX = Namespace("http://example.org/schema/")
    COMP = Namespace("http://example.org/company/")
    COURT = Namespace("http://example.org/court/")

    g = Graph()
    g.parse(ttl_path, format="turtle")

    print(f"📂 Loaded {len(g)} triples from {os.path.basename(ttl_path)}")

    companies = {}
    for s in g.subjects(RDF.type, EX.Company):
        company = {
            "uri": s,
            "companyName": None,
            "courtName": None,
            "registrationCode": None,
            "registrationYear": None,
            "courtURI": None,
            "fileName": None
        }

        for _, p, o in g.triples((s, None, None)):
            val = normalize_text(str(o).strip())
            if p == EX.companyName:
                company["companyName"] = val
            elif p == EX.registrationCode:
                company["registrationCode"] = val
            elif p == EX.registrationYear:
                company["registrationYear"] = val
            elif p == EX.fileName:
                company["fileName"] = val
            elif p == EX.registeredAt:
                company["courtURI"] = o

        # Resolve courtName
        if company["courtURI"]:
            for _, p, o in g.triples((company["courtURI"], EX.courtName, None)):
                company["courtName"] = normalize_text(str(o).strip())

        companies[s] = company

    print(f"🔍 Extracted {len(companies)} company entities.")

    # Filtering
    filtered = []
    for c in companies.values():
        cname = (c["companyName"] or "").lower()
        court = (c["courtName"] or "").lower()
        regcode = c["registrationCode"]
        regyear = c["registrationYear"]

        if cname == court == (regcode or "").lower() == (regyear or "").lower():
            continue
        if any(x in court for x in ["polizei", "stadtkämmerei", "juſtizminiſter"]):
            continue
        if not c["courtName"] and not c["registrationCode"]:
            continue
        if not any(x in court for x in ["amt", "regricht"]):
            continue
        if cname.strip() == "gesellschaft mit beschraenkter haftung":
            continue

        filtered.append(c)

    print(f"✅ Remaining after filtering: {len(filtered)} entities")

    # Deduplication (fewest nulls)
    deduped = {}
    for c in filtered:
        name = c["companyName"]
        if not name:
            continue
        nulls = sum(v in (None, "") for v in [c["courtName"], c["registrationCode"], c["registrationYear"]])
        if name not in deduped or nulls < deduped[name]["_null_count"]:
            c["_null_count"] = nulls
            deduped[name] = c

    print(f" Deduplicated to {len(deduped)} unique company names")

    # Rebuild TTL graph
    g_new = Graph()
    g_new.bind("ex", EX)
    g_new.bind("comp", COMP)
    g_new.bind("court", COURT)

    for c in deduped.values():
        comp_uri = c["uri"]
        g_new.add((comp_uri, RDF.type, EX.Company))
        g_new.add((comp_uri, EX.companyName, Literal(c["companyName"])))

        if c["registrationCode"]:
            g_new.add((comp_uri, EX.registrationCode, Literal(c["registrationCode"])))
        if c["registrationYear"]:
            g_new.add((comp_uri, EX.registrationYear, Literal(c["registrationYear"])))
        if c["fileName"]:
            g_new.add((comp_uri, EX.fileName, Literal(c["fileName"])))

        if c["courtName"]:
            court_uri = c["courtURI"] or COURT[c["courtName"].replace(" ", "_")]
            g_new.add((court_uri, RDF.type, EX.Court))
            g_new.add((court_uri, EX.courtName, Literal(c["courtName"])))
            g_new.add((comp_uri, EX.registeredAt, court_uri))

    g_new.serialize(destination=output_path, format="turtle")
    print(f"💾 Cleaned TTL saved to: {output_path}")
    print(f"📊 Final triple count: {len(g_new)}")


if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    folder_path = os.path.join(BASE_DIR, "data", "processed", "DE_newspapers_1920_45_processed", "Qlever")

    input_ttl = os.path.join(folder_path, "DE_1920_45_comb_ontology.ttl")
    output_ttl = os.path.join(folder_path, "DE_1920_45_comb_ontology_cleaned.ttl")

    postprocess_ttl(input_ttl, output_ttl)
