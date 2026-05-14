"""
Minimal Wikidata query – only country of citizenship and date cutoff are dynamic.
To determine parameters, see:
- For A-3 country abbreviations: https://en.wikipedia.org/wiki/List_of_ISO_3166_country_codes
- For country qid, search:   https://www.wikidata.org/wiki/Special:Search
- ForPublic Domain date cutoff: https://upload.wikimedia.org/wikipedia/commons/5/59/World_copyright_terms.svg
"""

from datetime import datetime
import json
import os
from SPARQLWrapper import SPARQLWrapper, JSON

# =====================================================================
# DYNAMIC PARAMETERS – the only things you need to change per country
# =====================================================================
COUNTRY_ABBREV = "NIC"             # used in the output filename (3-letter ISO code)
COUNTRY_QID  = "wd:Q811"            # Wikidata item for the country (include "wd:")
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

# Dynamic output filename: output/authors_venezuela.json (example)
QUERY_DATE = datetime.now().strftime("%Y-%m-%d")
output_filename = f"output/{COUNTRY_ABBREV}/authors_{COUNTRY_ABBREV}_{QUERY_DATE}.json"

# Create output directory if it doesn't exist
os.makedirs(os.path.dirname(output_filename), exist_ok=True)

# Query Wikidata and save results to JSON file
sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
sparql.agent = "MOREL/2.0 (contact: eduardofebres@gmail.com)"
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