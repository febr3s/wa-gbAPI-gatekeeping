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
data = response.json()

# 5. ADD REQUEST URI AND ACTUAL ITEM COUNT
data['getRequest'] = url  # Add just the URI string
data['totalItems'] = len(data.get('items', []))

# 6. SAVE RAW RESPONSE TO FILE
output_dir = 'raw_gbooks_data'
os.makedirs(output_dir, exist_ok=True)

safe_name = author_name.replace(' ', '_')
filename = f"{output_dir}/{safe_name}-{author_viaf}.json"

with open(filename, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

# 7. PRINT CONFIRMATION
print(f"✅ Raw data saved to: {filename}")
print(f"   Items in the saved file: {data['totalItems']}")