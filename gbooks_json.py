import os
import requests
import json

# 1. LOAD API KEY
API_KEY = os.environ.get('GOOGLE_BOOKS_API_KEY')
if not API_KEY:
    print("ERROR: Set the 'GOOGLE_BOOKS_API_KEY' environment variable first.")
    exit()

# 2. LOAD AUTHOR FROM JSON FILE
with open('venezuelan_authors_test.json', 'r', encoding='utf-8') as f:
    author_data = json.load(f)

# Extract the third author's label (Francisco de Miranda)
# Using results['bindings'][2] as it's the third item (0-indexed)
try:
    author = author_data['results']['bindings'][2]['authorLabel']['value']
except (KeyError, IndexError):
    print("ERROR: Could not find the third author in the JSON file.")
    exit()

# 3. DEFINE THE EXACT REQUEST URL
# Use urllib.parse.quote to properly encode the author name
from urllib.parse import quote
encoded_author = quote(author)
url = f'https://www.googleapis.com/books/v1/volumes?q=inauthor:"{encoded_author}"&maxResults=20&key={API_KEY}'

# 4. MAKE THE REQUEST
print(f"Searching for author: {author}")
print(f"Requesting: {url[:80]}...")
response = requests.get(url)
data = response.json()

# 5. PRINT RAW RESULT COUNT
total = data.get('totalItems', 0)
items = data.get('items', [])
print(f"\nFound {total} total items. Showing {len(items)} in this batch.")

# 6. QUICK CHECK FOR EXACT MATCHES
print("\nChecking authors in each result:")
for i, book in enumerate(items):
    title = book['volumeInfo'].get('title', 'No title')
    authors = book['volumeInfo'].get('authors', ['No authors listed'])
    exact_match = author in authors  # Check if author name is in the list
    print(f"  {i+1}. {title[:40]}...")
    print(f"     Authors: {authors}")
    print(f"     Exact match? {exact_match}\n")