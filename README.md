# German Company Register Analysis

## Problem Statement

In Germany, the incorporation of companies (and subsequent changes) is handled not by a central register but by district courts (**Amtsgerichte**). Around 150 courts (out of a total of 600) are responsible for company registrations. However, the current system has several issues:

- **Lack of uniqueness**: The identifiers issued by each court are not unique to Germany.
- **Inconsistent representation**: There is no official or standardized way to represent these identifiers.
- **Multiple registrations**: When a company moves its headquarters from one court district to another, it receives a new identifier, causing fragmentation.

## Project Focus

This repository focuses on **understanding and visualizing company registrations across various courts in Germany**. The data consists of all **commercial, cooperative, company, association, and partnership registers** referenced by the **XJustizID**. The dataset is an excerpt from the **judicial directory of places and courts**.

## Actions Taken

1. **Extracted Data from Excel Files**:
   - The raw data was in Excel format, containing court names, register types, postal codes, and XJustizID mappings.
   - Processed and converted this data into **RDF triples**.

2. **Triples Generation & Indexing**:
   - RDF triples were generated using **Python (Pandas, rdflib)**.
   - Added metadata, including **versioning and validity periods**.
   - Indexed the triples using **QLever**, a powerful SPARQL-based querying system.

3. **Querying the Data**:
   - The indexed data can be queried **locally** using **QLever**.
   - Example SPARQL queries allow retrieving company registration details, identifier mappings, and court jurisdictions.

## How to Run the Project

### Prerequisites
- Python 3.10+
- Poetry (version 1.8.4) for dependency management
- Docker (for running QLever)

### Setup
1. **Clone the repository**
   ```bash
   git clone https://github.com/Abhinandan707/KG4CR.git
   cd KG4CR
   ```

2. **Install dependencies**
   ```bash
   poetry install
   ```

3. **Prepare the data**
   - Place the Excel files in the `data/raw_data/` directory.
   - Run the RDF conversion script:
     ```bash
     poetry run python generate_rdf.py
     ```

4. **Index the data using QLever**
   ```bash
   cd data\processed
   qlever index
   ```

5. **Start QLever engine**
   ```bash
   qlever start
   ```
5. **Access UI for querying**
   ```bash
   qlever ui
   ```
   - Access QLever at: [http://localhost:PORT](http://localhost:PORT) 

5. **Integrate backend & start querying**
   - This is the default Qlever localhost view:
   ![qlever_default_localhost](images\qlever_default_localhost.png)
    - Go to '*Resources*' (right corner) -> '*QLever UI Admin*' 
    - Log in using *Username*: 'demo' and *password* : 'demo'
    - Go to '*Backends*' -> '*Add*' & enter details as shown below and click on *save* at the end of the page.
    ![kg4cr_backend_settings](images\kg4cr_backend_settings.png)
    - Come back to the default view and select an option 'kg4cr' from the left-corner dropdown.

### Example Query
Retrieve all courts with their **XJustizID, postal codes, and register types**:
```sparql
PREFIX ex: <http://example.org/schema#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?courtLabel ?xJustizID ?postalCode ?registerType
WHERE {
    ?court a ex:RegisterCourt ;
           rdfs:label ?courtLabel ;
           ex:hasXJustizID ?xJustizID ;
           ex:hasPostalCode ?postalCode ;
           ex:hasRegisterType ?registerType .
}
```

## Future Work
- Improve data completeness and consistency.
- Expand the dataset to include more courts.
- Integrate addional KGs (especially company registration data) to enrich the visualization

---
This project aims to bring more transparency to Germany’s decentralized **company registration system** by providing a structured and queryable **knowledge graph**.

