import requests
import os

API_KEY = os.environ.get('GOOGLE_BOOKS_API_KEY')
url_with_key = f'https://www.googleapis.com/books/v1/volumes?q=inauthor:"Leoncio+Martínez"&key={API_KEY}'
url_without_key = 'https://www.googleapis.com/books/v1/volumes?q=inauthor:"Leoncio+Martínez"'

# Test request WITH key
response_with = requests.get(url_with_key)
print("--- WITH API KEY ---")
print(f"Status Code: {response_with.status_code}")
if response_with.status_code != 200:
    print(f"Error Body: {response_with.text[:200]}")  # Print first 200 chars of error

# Test request WITHOUT key
response_without = requests.get(url_without_key)
print("\n--- WITHOUT API KEY ---")
print(f"Status Code: {response_without.status_code}")