import os
import requests
import json
from urllib.parse import quote
import time  # For adding a delay between requests

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

# 3. BASE SETUP
encoded_author = quote(author_name)
safe_name = author_name.replace(' ', '_')
output_dir = 'raw_gbooks_data'
os.makedirs(output_dir, exist_ok=True)

# 4. PAGINATION LOGIC - SINGLE FILE OUTPUT
all_items = []
max_results = 20
start_index = 0
request_count = 0
request_urls = []  # To log all URLs, including rescue requests
first_request_url = None
initial_total_estimate = 0

print(f"Starting consolidated fetch for author: {author_name}")
print("=" * 50)

while True:
    request_count += 1
    
    # Build the URL for the current request
    current_url = f'https://www.googleapis.com/books/v1/volumes?q=inauthor:"{encoded_author}"&maxResults={max_results}&startIndex={start_index}&key={API_KEY}'
    request_urls.append(current_url)
    
    if first_request_url is None:
        first_request_url = current_url
    
    print(f"Request #{request_count}: startIndex={start_index}")
    
    # Make the request with basic error handling
    try:
        response = requests.get(current_url)
        response.raise_for_status()  # Raise an error for bad status codes (4xx, 5xx)
        current_data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"   ⚠️ Request failed: {e}. Skipping this batch.")
        break  # Or implement a retry logic here
    
    current_total_estimate = current_data.get('totalItems', 0)
    current_items = current_data.get('items', [])
    fetched_count = len(current_items)
    
    # Save the initial totalItems estimate from the very first response
    if request_count == 1:
        initial_total_estimate = current_total_estimate
    
    # TERMINATION RULE 1: totalItems is 0
    if current_total_estimate == 0:
        print("   'totalItems' is 0. Stopping.")
        break
    
    # BUG WORKAROUND: Items list is empty but totalItems > 0
    if fetched_count == 0 and current_total_estimate > 0:
        print(f"   ⚠️ BUG: No 'items' but 'totalItems'={current_total_estimate}. Attempting rescue...")
        
        # RESCUE REQUEST: Use totalItems as maxResults for this startIndex
        rescue_url = f'https://www.googleapis.com/books/v1/volumes?q=inauthor:"{encoded_author}"&maxResults={current_total_estimate}&startIndex={start_index}&key={API_KEY}'
        request_urls.append(rescue_url)  # Log the rescue attempt
        print(f"   Rescue request: maxResults={current_total_estimate}")
        
        try:
            rescue_response = requests.get(rescue_url)
            rescue_data = rescue_response.json()
            rescue_items = rescue_data.get('items', [])
            
            if rescue_items:
                print(f"   ✓ Rescue successful, adding {len(rescue_items)} items.")
                all_items.extend(rescue_items)
            else:
                print("   ✗ Rescue also returned no items.")
        except requests.exceptions.RequestException as e:
            print(f"   ✗ Rescue request failed: {e}")
        
        # After a rescue attempt (successful or not), this is the end.
        break
    
    # NORMAL CASE: Items were received
    if fetched_count > 0:
        print(f"   ✓ Fetched {fetched_count} items.")
        all_items.extend(current_items)
    
    # TERMINATION RULE 2: Natural end of results (partial page)
    if fetched_count < max_results:
        print(f"   Partial page received. Assuming end of results.")
        break
    
    # PREPARE FOR NEXT ITERATION
    start_index += max_results
    
    # Small delay to be polite to the API and avoid rate limits
    time.sleep(0.1)

# 5. CREATE FINAL CONSOLIDATED DATA STRUCTURE
print("\n" + "=" * 50)
print("Building final consolidated output...")

final_data = {
    "getRequest": first_request_url,  # The very first request URL
    "_requestUrls": request_urls,     # List of ALL URLs tried (for debugging)
    "_totalQueriedItems": initial_total_estimate,  # totalItems from first response
    "_totalFetchedItems": len(all_items),  # Actual number of items collected
    "_totalRequestsMade": request_count,
    "_batchSizeUsed": max_results,
    "items": all_items  # All items from all successful batches
}

# 6. SAVE SINGLE OUTPUT FILE
final_filename = f"{output_dir}/{safe_name}-{author_viaf}-CONSOLIDATED.json"
with open(final_filename, 'w', encoding='utf-8') as f:
    json.dump(final_data, f, indent=2, ensure_ascii=False)

print(f"✅ FINAL FILE SAVED: {final_filename}")
print(f"   Initial API estimate: {initial_total_estimate} items")
print(f"   Successfully fetched: {len(all_items)} items")
print(f"   Total HTTP requests: {request_count}")
print("=" * 50)