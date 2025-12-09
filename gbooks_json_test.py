import os
import requests
import json
from urllib.parse import quote

# 1. LOAD API KEY
API_KEY = os.environ.get('GOOGLE_BOOKS_API_KEY')
if not API_KEY:
    print("ERROR: Set the 'GOOGLE_BOOKS_API_KEY' environment variable first.")
    exit()

# 2. LOAD AUTHOR FROM JSON FILE
with open('venezuelan_authors_test.json', 'r', encoding='utf-8') as f:
    author_data = json.load(f)

# Extract the third author's data
try:
    target_author = author_data['results']['bindings'][2]
    author_name = target_author['authorLabel']['value']
    author_viaf = target_author.get('viaf', {}).get('value', 'NO_VIAF')
except (KeyError, IndexError):
    print("ERROR: Could not find the third author's data in the JSON file.")
    exit()

# 3. DEFINE THE EXACT REQUEST URL
encoded_author = quote(author_name)
url = f'https://www.googleapis.com/books/v1/volumes?q=inauthor:"{encoded_author}"&maxResults=20&key={API_KEY}'

# 4. MAKE THE REQUEST
print(f"Searching for author: {author_name}")
response = requests.get(url)
api_data = response.json()

# 5. CREATE NEW ORDERED DICTIONARY WITH getRequest FIRST
final_data = {}
final_data['getRequest'] = url
final_data['kind'] = api_data.get('kind')
final_data['totalItems'] = len(api_data.get('items', []))
final_data['items'] = api_data.get('items', [])
# Copy any other remaining fields
for key, value in api_data.items():
    if key not in final_data:
        final_data[key] = value

# 6. SAVE TO FILE - Using json.dumps with ensure_ascii=False
output_dir = 'raw_gbooks_data'
os.makedirs(output_dir, exist_ok=True)

safe_name = author_name.replace(' ', '_')
filename = f"{output_dir}/{safe_name}-{author_viaf}.json"

with open(filename, 'w', encoding='utf-8') as f:
    # json.dumps with ensure_ascii=False prevents escape sequences for quotes in URL
    json_string = json.dumps(final_data, indent=2, ensure_ascii=False)
    f.write(json_string)

# 7. PRINT CONFIRMATION
print(f"✅ Raw data saved to: {filename}")
print(f"   Items in the saved file: {final_data['totalItems']}")