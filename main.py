import os
import requests

# 1. LOAD API KEY
API_KEY = os.environ.get('GOOGLE_BOOKS_API_KEY')
if not API_KEY:
    print("ERROR: Set the 'GOOGLE_BOOKS_API_KEY' environment variable first.")
    exit()

# 2. DEFINE THE EXACT REQUEST URL (Your original one, with key)
author = 'Leoncio+Martínez'
url = f'https://www.googleapis.com/books/v1/volumes?q=inauthor:"{author}"&maxResults=20&key={API_KEY}'

# 3. MAKE THE REQUEST
print(f"Requesting: {url[:80]}...")
response = requests.get(url)
data = response.json()

# 4. PRINT RAW RESULT COUNT
total = data.get('totalItems', 0)
items = data.get('items', [])
print(f"\nFound {total} total items. Showing {len(items)} in this batch.")

# 5. QUICK CHECK FOR EXACT MATCHES
print("\nChecking authors in each result:")
for i, book in enumerate(items):
    title = book['volumeInfo'].get('title', 'No title')
    authors = book['volumeInfo'].get('authors', ['No authors listed'])
    exact_match = '"Leoncio Martínez"' in str(authors)  # Simple check
    print(f"  {i+1}. {title[:40]}...")
    print(f"     Authors: {authors}")
    print(f"     Exact match? {exact_match}\n")