import pandas as pd
import os
from combine_excels2df import combine_excel_into_df, preprocess_combined_df

def df_to_ttl(df, filename="output.ttl"):
    ttl_lines = [
        '@prefix ex: <http://example.org/schema#> .',
        '@prefix court: <http://example.org/RegisterCourt/> .',
        '@prefix xjid: <http://example.org/XJustizID/> .',
        '@prefix state: <http://example.org/State/> .',
        '@prefix rtype: <http://example.org/RegisterType/> .',
        '@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .',
        '@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .',
        '@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .',
        '',
        '### Classes',
        'ex:RegisterCourt a rdfs:Class ;',
        '    rdfs:label "Register Court"@en .',
        '',
        'ex:XJustizID a rdfs:Class ;',
        '    rdfs:label "XJustiz Identifier"@en .',
        '',
        'ex:RegisterType a rdfs:Class ;',
        '    rdfs:label "Register Type"@en .',
        '',
        'ex:State a rdfs:Class ;',
        '    rdfs:label "State"@en .',
        '',
        '### Properties',
        'ex:hasXJustizID a rdf:Property ;',
        '    rdfs:domain ex:RegisterCourt ;',
        '    rdfs:range ex:XJustizID ;',
        '    rdfs:label "has XJustiz ID"@en .',
        '',
        'ex:hasPostalCode a rdf:Property ;',
        '    rdfs:domain ex:XJustizID ;',
        '    rdfs:range xsd:string ;',
        '    rdfs:label "Postal Code"@en .',
        '',
        'ex:hasRegisterType a rdf:Property ;',
        '    rdfs:domain ex:XJustizID ;',
        '    rdfs:range ex:RegisterType ;',
        '    rdfs:label "Has Register Type"@en .',
        '',
        'ex:locatedIn a rdf:Property ;',
        '    rdfs:domain ex:XJustizID ;',
        '    rdfs:range ex:State ;',
        '    rdfs:label "Located In"@en .',
        '',
        'ex:validUntil a rdf:Property ;',
        '    rdfs:domain ex:XJustizID ;',
        '    rdfs:range xsd:date ;',
        '    rdfs:label "Valid Until"@en .',
        '',
        'ex:hasFutureCode a rdf:Property ;',
        '    rdfs:domain ex:XJustizID ;',
        '    rdfs:range xsd:string ;',
        '    rdfs:label "Future Code"@en .',
        '',
        '### Instances (Triples)',
        ''
    ]

    # Create unique court nodes
    unique_courts = df[['RegisterCourt']].drop_duplicates()
    for _, row in unique_courts.iterrows():
        court_uri = row['RegisterCourt'].replace(' ', '_').replace('(', '').replace(')', '') \
            .replace('ä', 'ae').replace('ü','ue').replace('ö','oe').replace('ß','ss')
        ttl_lines.append(f'court:{court_uri} a ex:RegisterCourt ;')
        ttl_lines.append(f'    rdfs:label "{row["RegisterCourt"]}"@de .\n')

    # Link courts to their XJustizIDs and create XJustizID nodes with properties
    for _, row in df.iterrows():
        court_uri = row['RegisterCourt'].replace(' ', '_').replace('(', '').replace(')', '') \
            .replace('ä', 'ae').replace('ü','ue').replace('ö','oe').replace('ß','ss')
        xjid = row['XJustizID']
        xjid_uri = f'xjid:{xjid}'

        # Link court to XJustizID
        ttl_lines.append(f'court:{court_uri} ex:hasXJustizID {xjid_uri} .')

        # Define XJustizID instance and its properties
        ttl_lines.append(f'{xjid_uri} a ex:XJustizID ;')
        ttl_lines.append(f'    ex:hasXJustizID "{xjid}"^^xsd:string ;')

        # Postal code
        plz = str(row['PLZ']) if pd.notna(row['PLZ']) else ''
        ttl_lines.append(f'    ex:hasPostalCode "{plz}"^^xsd:string ;')

        # RegisterType (can be multiple, split by comma)
        rtypes = str(row['RegisterType']).split(',')
        rtypes_clean = []
        for rt in rtypes:
            rt = rt.strip()
            rt_uri = rt.replace(' ', '_').replace('ü','ue').replace('ä','ae').replace('ö','oe').replace('ß','ss') \
                .replace('-', '_').replace('.', '').replace(',', '')
            rtypes_clean.append(f'rtype:{rt_uri}')
        ttl_lines.append(f'    ex:hasRegisterType {", ".join(rtypes_clean)} ;')

        # State
        state = row['State'].replace(' ', '').replace('ü','ue').replace('ä','ae').replace('ö','oe').replace('ß','ss')
        ttl_lines.append(f'    ex:locatedIn state:{state} ;')

        # ValidUntil date formatting
        valid_until = row['ValidUntil']
        if pd.notna(valid_until) and valid_until != 'NaN':
            try:
                day, month, year = valid_until.split('.')
                valid_until_formatted = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                ttl_lines.append(f'    ex:validUntil "{valid_until_formatted}"^^xsd:date ;')
            except Exception:
                pass

        # FutureCode
        future_code = str(row['FutureCode'])
        if future_code.lower() not in ['nan', 'none', ''] :
            ttl_lines.append(f'    ex:hasFutureCode "{future_code}"^^xsd:string ;')

        # End triple with dot (replace last semicolon)
        ttl_lines[-1] = ttl_lines[-1].rstrip(' ;') + ' .\n'

    # Write to file
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(ttl_lines))

    print(f"RDF Turtle file written to: {filename}")


if __name__ == "__main__":
    # Specify the folder path
    base_path = os.path.join(os.getcwd(), "..")  # go up one directory
    folder_path = os.path.join(base_path, "data", "raw_data")  # specify the folder path
    # Specify the output Turtle file path
    output_ttl_file = os.path.join(base_path, "data", "processed", 'with_Ontology', f"register_courts_combined.ttl")
    # Combine Excel files into a DataFrame
    combined_df = combine_excel_into_df(folder_path)

    # Preprocess the combined DataFrame
    final_df = preprocess_combined_df(combined_df)

    # Convert the DataFrame to Turtle format
    df_to_ttl(final_df, output_ttl_file)