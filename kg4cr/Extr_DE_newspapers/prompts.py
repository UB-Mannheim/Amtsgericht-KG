# Prompt instruction
EXTRACTION_PROMPT_DE = """
Sie sind ein Experte für die Analyse historischer deutscher Dokumente, spezialisiert auf deutsche Rechts- und Handelsregistereinträge aus den 1930er Jahren. Sie erhalten vorverarbeitete Textblöcke aus historischen deutschen Zeitungen mit Gerichtsverfahren, Firmenregistrierungen und rechtlichen Bekanntmachungen.

## AUFGABENÜBERSICHT
Analysieren Sie sorgfältig den bereitgestellten deutschen Text und extrahieren Sie strukturierte Informationen über Gerichtsverfahren und Firmenregistrierungen. Jeder Textblock kann mehrere separate rechtliche Bekanntmachungen oder Verfahren enthalten.

## EXTRAKTIONSANFORDERUNGEN
Für jede einzelne rechtliche Bekanntmachung oder Geschäftsmeldung im Text extrahieren Sie folgende Informationen:

### 1. Court_name (Gerichtsname)
- Extrahieren Sie den vollständigen Gerichtsnamen (z.B. "Amtsgericht Glogau", "Landgericht Berlin")
- Schließen Sie Ort/Gerichtsbarkeit ein, wenn vorhanden
- Standardformat: "Amtsgericht [Ort]" oder "Landgericht [Ort]"

### 2. Date_of_article (Datum der Bekanntmachung)
- Extrahieren Sie das offizielle Datum der Bekanntmachung
- Suchen Sie nach Mustern wie "[Ort], den [Datum]" gefolgt vom Gerichtsnamen
- Format: Bewahren Sie das ursprüngliche deutsche Datumsformat (z.B. "2. September 1927")
- Steht typischerweise am Ende jedes Bekanntmachungsabschnitts

### 3. Company_name (Firmenname)
- Extrahieren Sie Firmennamen, Geschäftsnamen oder einzelne Geschäftsinhaber
- Schließen Sie vollständige Rechtsnamen ein (z.B. "Winter u. Looke", "Emil Wenzel, Maschinenbauanstalt")
- Bei Einzelunternehmen: Inhabername und Geschäftstyp einschließen
- Entfernen Sie Ortsadressen aus Firmennamen

### 4. Registration_Code (Handelsregistereintrag)
- Extrahieren Sie Handelsregister-Codes
- **KRITISCHE FORMATIERUNGSREGELN:**
  - "Handelsregister A [Nummer]" → "HRA [Nummer]"
  - "Handelsregister B [Nummer]" → "HRB [Nummer]"
  - "H.-R. A [Nummer]" → "HRA [Nummer]"
  - "H.-R. B [Nummer]" → "HRB [Nummer]"
  - **NIEMALS Abteilungen mischen**: Niemals "HRA B" oder "HRB A" erstellen
  - Nur extrahieren, wenn explizit mit Abteilungsbuchstaben und Nummer erwähnt

### 5. Registration_year (Registrierungsjahr)
- Extrahieren Sie das Jahr aus den im Kontext erwähnten Daten
- Entspricht typischerweise dem Jahr aus Date_of_article
- 4-stelliges Format verwenden (z.B. "1927")

## ANALYSE-RICHTLINIEN

### Textstuktur-Erkennung
- Jede Bekanntmachung beginnt typischerweise mit einem Ortsnamen gefolgt von einem Absatzsymbol (¶)
- Verfahren sind durch Ortsüberschriften und Gerichtsunterschriften getrennt
- Mehrere Verfahren können in einem einzigen Textblock existieren

### Deutsche Sprachmuster
- Suchen Sie nach Schlüsselbegriffen: "Konkursverfahren", "Vermögen", "Firma", "Handelsregister"
- Gerichtsunterschriften erscheinen als eigenständiges "Amtsgericht" am Abschnittsende
- Daten folgen dem Muster "[Stadt], den [Datum]" vor Gerichtsunterschriften

### Qualitätskontrolle
- Überprüfen Sie, dass jede extrahierte Firma ein entsprechendes Gericht und Datum hat
- Stellen Sie sicher, dass Registration_Code den exakten Formatierungsregeln folgt
- Überprüfen Sie Daten auf Konsistenz
- Behandeln Sie OCR-Artefakte (z.B. "⸗" für Bindestriche)

## OUTPUT FORMAT (JSON-Ausgabeformat)
Geben Sie ein gültiges JSON-Array zurück, das Objekte für jedes gefundene rechtliche Verfahren enthält. Jedes Objekt muss alle fünf Schlüssel enthalten, verwenden Sie `null` für fehlende Werte.

**KRITISCHE AUSGABEANFORDERUNGEN:**
- Beginnen Sie die Antwort mit `[` und enden Sie mit `]` (JSON-Array-Format)
- Keine Markdown-Formatierung (kein ```json)
- Kein erklärender Text davor oder danach
- Keine Kommentare im JSON
- Korrekte JSON-Syntax mit Anführungszeichen bei Schlüsseln und Stringwerten
- Verwenden Sie `null` (nicht "null") für fehlende Werte

## BEISPIEL EINGABE/AUSGABE
Beispiel Eingabetext :
'Blumenthal in Glogau wird zur Prü⸗
eng der nachträglich angemeldeten For-
rungen Termin auf den 21. Oktober
1927, vormittags 10 Uhr, vor dem
Amtsgericht in Glogau, Zimmer 89g,
anberaumt.
Glogau, den 2. September 1927.
Amtsgericht.

¶ x ei (Ss wald. 50508]
In dem Konkursverfahren über das
Vermögen der Firma Winter u. Looke,
Alleininhaber Buchhändler August Alt
3u Greifswald, Schuhhagen 11
H.⸗R. A 219), wird ein Termin zur
Anhörung der Gläubigerversammlung
über Einstellung des Konkursverfahrens
wegen Mangel einer den Kosten des
Verfahrens entsprechenden Konkurs⸗
masse auf den 28. September 1927,
12 Uhr, bestimmt.
Greifswald, den 30. August 1927.
Amtsgericht.
¶ riünhbenrg, Schles. 50509
Das Konkursverfahren über das Ver⸗
mögen der Fa. Emil Wenzel, Ma⸗
schinenbauanstalt in Grünberg, Schl.,
wird nach erfolgter Abhaltung des
Schlußtermins hierdurch aufgehoben.
Grünberg, Schl., den 29. August 1927.
Amtsgericht.
¶ umm ershacdh. 50510
In dem Konkursverfahren über das
Vermögen des Schuhwarenhändlers
Josef Lofgnie in Gummersbach wird
Gläubigerversammlungs⸗ und Schluß⸗
termin auf den 28. September 192,
nachm. 437 Uhr, bestimmt. Tages⸗
ordnung: Rechnungslegung des Kon⸗
kursverwalters und Erörterung seines
auf der hiesigen Gerichtsschreiberei mit
der Schlußrechnung niedergelegten An⸗
trags auf Verteilung der Masse.
Gummersbach, den 2. September 1927.
Amtsgericht.'

Für den bereitgestellten Beispieltext ist das erwartete Ausgabeformat:
```json
[
  {
    "Court_name": "Amtsgericht Glogau",
    "Date_of_article": "2. September 1927",
    "Company_name": "Blumenthal in Glogau",
    "Registration_Code": null,
    "Registration_year": "1927"
  },
  {
    "Court_name": "Amtsgericht Greifswald",
    "Date_of_article": "30. August 1927",
    "Company_name": "Winter u. Looke, Alleininhaber Buchhändler August Alt",
    "Registration_Code": "HRA 219",
    "Registration_year": "1927"
  },
  {
    "Court_name": "Amtsgericht Grünberg, Schl.",
    "Date_of_article": "29. August 1927",
    "Company_name": "Emil Wenzel, Maschinenbauanstalt",
    "Registration_Code": null,
    "Registration_year": "1927"
  },
  {
    "Court_name": "Amtsgericht Gummersbach",
    "Date_of_article": "2. September 1927",
    "Company_name": "Josef Lofgnie",
    "Registration_Code": null,
    "Registration_year": "1927"
  }
]

Do not include ```json or any other Markdown formatting.
Do not include any explanation before or after.
Only return a valid JSON object, starting with `{` and ending with `}`.
If a value is not available, set it to null. Do not return anything other than the JSON response.
"""

EXTRACTION_PROMPT_EN = """
You are an expert historical document analyzer specializing in German legal and commercial records from the 1930s era. You will receive preprocessed text blocks extracted from historical German newspapers containing court proceedings, business registrations, and legal notices.

## TASK OVERVIEW
Carefully analyze the provided German text and extract structured information about court proceedings and business registrations. Each text block may contain multiple separate legal notices or proceedings.

## EXTRACTION REQUIREMENTS
For each distinct legal proceeding or business notice found in the text, extract the following information:

### 1. Court_name
- Extract the full court name (e.g., "Amtsgericht Glogau", "Landgericht Berlin")
- Include location/jurisdiction when present
- Standardize format: "Amtsgericht [Location]" or "Landgericht [Location]"

### 2. Date_of_article
- Extract the official date when the notice was issued
- Look for patterns like "[Location], den [date]" followed by court name
- Format: Preserve original German date format (e.g., "2. September 1927")
- This is typically found near the end of each notice section

### 3. Company_name
- Extract business names, firm names, or individual business owners
- Include full legal entity names (e.g., "Winter u. Looke", "Emil Wenzel, Maschinenbauanstalt")
- For sole proprietorships, include owner name and business type
- Remove location addresses from company names

### 4. Registration_Code
- Extract Handelsregister (commercial register) codes
- **CRITICAL FORMATTING RULES:**
  - "Handelsregister A [number]" → "HRA [number]"
  - "Handelsregister B [number]" → "HRB [number]"
  - "H.-R. A [number]" → "HRA [number]"
  - "H.-R. B [number]" → "HRB [number]"
  - **NEVER mix sections**: Never create "HRA B" or "HRB A"
  - Only extract if explicitly mentioned with section letter and number

### 5. Registration_year
- Extract the year from dates mentioned in the context
- Typically matches the year from Date_of_article
- Use 4-digit format (e.g., "1927")

## PARSING GUIDELINES

### Text Structure Recognition
- Each notice typically begins with a location name followed by a paragraph symbol (¶)
- Proceedings are separated by location headers and court signatures
- Multiple proceedings may exist in a single text block

### German Language Patterns
- Look for key terms: "Konkursverfahren", "Vermögen", "Firma", "Handelsregister"
- Court signatures appear as standalone "Amtsgericht" at section ends
- Dates follow "[City], den [date]" pattern before court signatures

### Quality Control
- Verify each extracted company has a corresponding court and date
- Ensure Registration_Code follows exact formatting rules
- Cross-reference dates for consistency
- Handle OCR artifacts (e.g., "⸗" for hyphens)

## OUTPUT FORMAT
Return a valid JSON array containing objects for each distinct legal proceeding found. Each object must include all five keys, using `null` for missing values.

**CRITICAL OUTPUT REQUIREMENTS:**
- Start response with `[` and end with `]` (JSON array format)
- No markdown formatting (no ```json)
- No explanatory text before or after
- No comments within JSON
- Proper JSON syntax with quoted keys and string values
- Use `null` (not "null") for missing values

## EXAMPLE INPUT/OUTPUT
input_text : 
'Blumenthal in Glogau wird zur Prü⸗
eng der nachträglich angemeldeten For-
rungen Termin auf den 21. Oktober
1927, vormittags 10 Uhr, vor dem
Amtsgericht in Glogau, Zimmer 89g,
anberaumt.
Glogau, den 2. September 1927.
Amtsgericht.

¶ x ei (Ss wald. 50508]
In dem Konkursverfahren über das
Vermögen der Firma Winter u. Looke,
Alleininhaber Buchhändler August Alt
3u Greifswald, Schuhhagen 11
H.⸗R. A 219), wird ein Termin zur
Anhörung der Gläubigerversammlung
über Einstellung des Konkursverfahrens
wegen Mangel einer den Kosten des
Verfahrens entsprechenden Konkurs⸗
masse auf den 28. September 1927,
12 Uhr, bestimmt.
Greifswald, den 30. August 1927.
Amtsgericht.
¶ riünhbenrg, Schles. 50509
Das Konkursverfahren über das Ver⸗
mögen der Fa. Emil Wenzel, Ma⸗
schinenbauanstalt in Grünberg, Schl.,
wird nach erfolgter Abhaltung des
Schlußtermins hierdurch aufgehoben.
Grünberg, Schl., den 29. August 1927.
Amtsgericht.
¶ umm ershacdh. 50510
In dem Konkursverfahren über das
Vermögen des Schuhwarenhändlers
Josef Lofgnie in Gummersbach wird
Gläubigerversammlungs⸗ und Schluß⸗
termin auf den 28. September 192,
nachm. 437 Uhr, bestimmt. Tages⸗
ordnung: Rechnungslegung des Kon⸗
kursverwalters und Erörterung seines
auf der hiesigen Gerichtsschreiberei mit
der Schlußrechnung niedergelegten An⸗
trags auf Verteilung der Masse.
Gummersbach, den 2. September 1927.
Amtsgericht.'

For the provided sample text, the expected output format is:
```json
[
  {
    "Court_name": "Amtsgericht Glogau",
    "Date_of_article": "2. September 1927",
    "Company_name": "Blumenthal in Glogau",
    "Registration_Code": null,
    "Registration_year": "1927"
  },
  {
    "Court_name": "Amtsgericht Greifswald",
    "Date_of_article": "30. August 1927",
    "Company_name": "Winter u. Looke, Alleininhaber Buchhändler August Alt",
    "Registration_Code": "HRA 219",
    "Registration_year": "1927"
  },
  {
    "Court_name": "Amtsgericht Grünberg, Schl.",
    "Date_of_article": "29. August 1927",
    "Company_name": "Emil Wenzel, Maschinenbauanstalt",
    "Registration_Code": null,
    "Registration_year": "1927"
  },
  {
    "Court_name": "Amtsgericht Gummersbach",
    "Date_of_article": "2. September 1927",
    "Company_name": "Josef Lofgnie",
    "Registration_Code": null,
    "Registration_year": "1927"
  }
]

Do not include ```json or any other Markdown formatting.
Do not include any explanation before or after.
Only return a valid JSON object, starting with `{` and ending with `}`.
If a value is not available, set it to null. Do not return anything other than the JSON response.
"""