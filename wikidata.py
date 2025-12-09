'''
This is a minimal query. In the future, more complex queries can be built. 
'''

# json is a built-in module - no installation needed!
import json
from SPARQLWrapper import SPARQLWrapper, JSON

# Your SPARQL query remains the same
query_string = """
SELECT DISTINCT ?author ?authorLabel ?date_of_death ?viaf WHERE {
  ?author wdt:P31 wd:Q5;                 # Instance of human
          wdt:P27 wd:Q717;               # Country: Venezuela
          wdt:P570 ?date_of_death;       # Date of death
          wdt:P214 ?viaf                 # VIAF code
  FILTER(?date_of_death < "1965-01-01"^^xsd:dateTime)
  
  
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
}
ORDER BY ?date_of_death
"""

sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
sparql.setReturnFormat(JSON)
sparql.setQuery(query_string)

try:
    data = sparql.queryAndConvert()
    
    # Save to JSON file using the built-in json module
    with open("venezuelan_authors.json", 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, indent=2, ensure_ascii=False)
    
    print(f"✓ Results saved to 'venezuelan_authors.json'")
    print(f"✓ Found {len(data['results']['bindings'])} authors")

except Exception as e:
    print(f"An error occurred: {e}")