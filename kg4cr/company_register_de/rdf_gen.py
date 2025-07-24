import pandas as pd
import os

def df_to_ttl(df, filename="output.ttl"):
    ttl_lines = [
        '@prefix ex: <http://example.org/schema#> .',
        '@prefix court: <http://example.org/RegisterCourt/> .',
        '@prefix company: <http://example.org/Company/> .',
        '@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .',
        '',
        '### Classes',
        'ex:Company a rdfs:Class ;',
        '    rdfs:label "Company"@en .',
        '',
        'ex:RegisterCourt a rdfs:Class ;',
        '    rdfs:label "Register Court"@en .',
        '',
        '### Properties',
        'ex:hasOpenCorporatesID a rdf:Property ;',
        '    rdfs:domain ex:Company ;',
        '    rdfs:range xsd:string ;',
        '    rdfs:label "Has OpenCorporates ID"@en .',
        '',
        'ex:hasCompanyName a rdf:Property ;',
        '    rdfs:domain ex:Company ;',
        '    rdfs:range xsd:string ;',
        '    rdfs:label "Has Company Name"@en .',
        '',
        'ex:hasCity a rdf:Property ;',
        '    rdfs:domain ex:Company ;',
        '    rdfs:range xsd:string ;',
        '    rdfs:label "Has City"@en .',
        '',
        '### Instances (Triples)',
        ''
    ]

    # Iterate over the DataFrame and generate RDF triples
    for _, row in df.iterrows():
        company_uri = row['CompanyName'].replace(' ', '_').replace('ä', 'ae').replace('ü','ue').replace('ö','oe').replace('ß','ss')
        open_corp_id = row['OpenCorporatesID']
        country_code, register_office, company_number = open_corp_id.split('/')[0], open_corp_id.split('/')[1].split('_')[0], open_corp_id.split('_')[1]
        
        ttl_lines.append(f'company:{company_uri} a ex:Company ;')
        ttl_lines.append(f'    ex:hasOpenCorporatesID "{open_corp_id}"^^xsd:string ;')
        ttl_lines.append(f'    ex:hasCompanyName "{row["CompanyName"]}"^^xsd:string ;')

        # Optional: Include city if available
        city = row.get('City', '')
        if city:
            ttl_lines.append(f'    ex:hasCity "{city}"^^xsd:string ;')

        ttl_lines.append(f'    ex:hasOpenCorporatesID "{open_corp_id}"^^xsd:string ;')

        # End triple with dot (replace last semicolon)
        ttl_lines[-1] = ttl_lines[-1].rstrip(' ;') + ' .\n'

    # Write the RDF Turtle content to a file
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(ttl_lines))

    print(f"RDF Turtle file written to: {filename}")


# Example usage
df = pd.read_csv('your_file.csv', sep='\t')  # Adjust the separator as needed
df_to_ttl(df, "companies_output.ttl")

