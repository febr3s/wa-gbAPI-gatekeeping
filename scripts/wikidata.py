"""
Minimal Wikidata query – only country of citizenship and date cutoff are dynamic.
For reference on Wikidata entity codes (Q-items and P-properties), see:
- Property list: https://www.wikidata.org/wiki/Wikidata:List_of_properties
- Item search:   https://www.wikidata.org/wiki/Special:Search
- Public Domain cutoff: https://upload.wikimedia.org/wikipedia/commons/5/59/World_copyright_terms.svg
"""

import json
import os
from SPARQLWrapper import SPARQLWrapper, JSON

# =====================================================================
# DYNAMIC PARAMETERS – the only things you need to change per country
# =====================================================================
COUNTRY_NAME = "guam"          # used in the output filename (no spaces, lowercase)
COUNTRY_QID  = "wd:Q16635"            # Wikidata item for the country (include "wd:")
DATE_CUTOFF  = "1956-01-01"         # include deaths before this date (YYYY-MM-DD)
# =====================================================================

# Build the SPARQL query – only the country value and the cutoff are inserted.
# Double braces {{ }} are literal braces needed inside the f‑string for SPARQL.
query_string = f"""
SELECT DISTINCT ?author ?authorLabel ?date_of_death ?viaf WHERE {{
  ?author wdt:P31 wd:Q5;                  # instance of: human
          wdt:P27 {COUNTRY_QID};          # country of citizenship
          wdt:P570 ?date_of_death;        # date of death
          wdt:P214 ?viaf.                 # VIAF identifier
  FILTER(?date_of_death < "{DATE_CUTOFF}"^^xsd:dateTime)

  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
}}
ORDER BY ?date_of_death
"""

# Create output directory if it doesn't exist
os.makedirs("output", exist_ok=True)

# Dynamic output filename: output/authors_venezuela.json (example)
output_filename = f"output/authors_{COUNTRY_NAME}.json"

sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
sparql.setReturnFormat(JSON)
sparql.setQuery(query_string)

try:
    data = sparql.queryAndConvert()

    with open(output_filename, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, indent=2, ensure_ascii=False)

    print(f"✓ Results saved to '{output_filename}'")
    print(f"✓ Found {len(data['results']['bindings'])} authors")

except Exception as e:
    print(f"An error occurred: {e}")