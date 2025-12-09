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

# 3. BASE URL COMPONENTS
encoded_author = quote(author_name)
output_dir = 'raw_gbooks_data'
os.makedirs(output_dir, exist_ok=True)
safe_name = author_name.replace(' ', '_')

# 4. PAGINATION LOGIC
max_results = 20
start_index = 0
request_count = 1
all_files_exported = False

def save_data_file(data_to_save, count):
    filename_counted = f"{output_dir}/{safe_name}-{author_viaf} ({count}).json"
    with open(filename_counted, 'w', encoding='utf-8') as f:
        json.dump(data_to_save, f, indent=2, ensure_ascii=False)
    print(f"✅ Batch {count} saved to: {filename_counted}")
    print(f"   Items in this batch: {len(data_to_save.get('items', []))}")

while not all_files_exported:
    # Build the URL for the current request
    current_url = f'https://www.googleapis.com/books/v1/volumes?q=inauthor:"{encoded_author}"&maxResults={max_results}&startIndex={start_index}&key={API_KEY}'
    
    print(f"\n--- Request #{request_count} (startIndex={start_index}) ---")
    print(f"Requesting: {current_url[:100]}...")
    
    response = requests.get(current_url)
    current_data = response.json()
    current_data['getRequest'] = current_url
    
    current_total_items = current_data.get('totalItems', 0)
    current_items_list = current_data.get('items', [])
    current_items_count = len(current_items_list)
    
    # RULE: If totalItems is 0, save and finish.
    if current_total_items == 0:
        print("   'totalItems' is 0.")
        current_data['totalItems'] = 0
        save_data_file(current_data, request_count)
        print("Process finished (no results).")
        all_files_exported = True
        break
    
    # RULE: Handle Outcome 1 - Total items less than max results.
    if current_total_items < max_results:
        print(f"   'totalItems' ({current_total_items}) < 'maxResults' ({max_results}).")
        print("   Making final request for remaining items...")
        
        final_url = f'https://www.googleapis.com/books/v1/volumes?q=inauthor:"{encoded_author}"&maxResults={current_total_items}&startIndex={start_index}&key={API_KEY}'
        final_response = requests.get(final_url)
        final_data = final_response.json()
        final_data['getRequest'] = final_url
        final_data['totalItems'] = len(final_data.get('items', []))
        
        save_data_file(final_data, request_count)
        print("Process finished (final batch retrieved).")
        all_files_exported = True
        break
    
    # RULE: Handle Outcome 2 - Items are present.
    if current_items_count > 0:
        current_data['totalItems'] = current_items_count
        save_data_file(current_data, request_count)
        
        request_count += 1
        start_index += max_results
    else:
        # Case where items list is empty but totalItems > 0.
        print(f"   No 'items' in response, but 'totalItems' is {current_total_items}.")
        print("   Skipping file export and moving to final batch logic...")
        
        print("   Making final request using 'totalItems' as maxResults...")
        final_url = f'https://www.googleapis.com/books/v1/volumes?q=inauthor:"{encoded_author}"&maxResults={current_total_items}&startIndex={start_index}&key={API_KEY}'
        final_response = requests.get(final_url)
        final_data = final_response.json()
        final_data['getRequest'] = final_url
        final_data['totalItems'] = len(final_data.get('items', []))
        
        save_data_file(final_data, request_count)
        print("Process finished (final batch retrieved after empty response).")
        all_files_exported = True
        break

print(f"\n🎯 All pages processed. Exported {request_count} file(s).")