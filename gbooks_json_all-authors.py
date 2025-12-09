import os
import requests
import json
import time
from urllib.parse import quote
from datetime import datetime

# ================= CONFIGURATION =================
API_KEY = os.environ.get('GOOGLE_BOOKS_API_KEY')
INPUT_JSON_FILE = 'venezuelan_authors_test.json'
OUTPUT_BASE_DIR = 'raw_gbooks_data'
DELAY_BETWEEN_AUTHORS = 5  # Seconds to wait after finishing one author
DELAY_BETWEEN_PAGES = 0.3  # Seconds to wait between pagination requests for one author
BATCH_SIZE = 20

# ================= SETUP =================
if not API_KEY:
    print("ERROR: Set the 'GOOGLE_BOOKS_API_KEY' environment variable first.")
    exit()

os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)

# Load the author data
try:
    with open(INPUT_JSON_FILE, 'r', encoding='utf-8') as f:
        author_data = json.load(f)
    all_authors = author_data['results']['bindings']
    print(f"📚 Loaded data for {len(all_authors)} authors.")
except (KeyError, FileNotFoundError, json.JSONDecodeError) as e:
    print(f"ERROR: Could not load or parse '{INPUT_JSON_FILE}': {e}")
    exit()

# Prepare logs and summary
log_file_path = os.path.join(OUTPUT_BASE_DIR, f"run_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
summary_data = {
    "scriptRunTimestamp": datetime.now().isoformat(),
    "totalAuthorsQueried": len(all_authors),
    "authorsProcessed": [],
    "_config": {
        "delayBetweenAuthors": DELAY_BETWEEN_AUTHORS,
        "delayBetweenPages": DELAY_BETWEEN_PAGES,
        "batchSize": BATCH_SIZE
    }
}

# ================= CORE PAGINATION FUNCTION =================
def fetch_all_books_for_author(author_name, author_viaf):
    """
    Fetches ALL books for a given author using the consolidated pagination logic
    with bug workarounds. Returns a dictionary ready for export.
    """
    encoded_name = quote(author_name)
    safe_name = author_name.replace(' ', '_')
    
    all_items = []
    start_index = 0
    request_count = 0
    request_urls = []
    first_request_url = None
    initial_total_estimate = 0
    
    print(f"   Starting fetch for '{author_name}'...")
    
    while True:
        request_count += 1
        
        # Build request URL
        current_url = f'https://www.googleapis.com/books/v1/volumes?q=inauthor:"{encoded_name}"&maxResults={BATCH_SIZE}&startIndex={start_index}&key={API_KEY}'
        request_urls.append(current_url)
        
        if first_request_url is None:
            first_request_url = current_url
        
        # Make request
        try:
            response = requests.get(current_url, timeout=30)
            response.raise_for_status()
            current_data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"      ⚠️ Request #{request_count} failed: {e}")
            break  # Stop pagination for this author on request error
        
        current_total_estimate = current_data.get('totalItems', 0)
        current_items = current_data.get('items', [])
        fetched_count = len(current_items)
        
        if request_count == 1:
            initial_total_estimate = current_total_estimate
        
        # TERMINATION RULE 1: totalItems is 0
        if current_total_estimate == 0:
            print(f"      No results found (totalItems=0).")
            break
        
        # BUG WORKAROUND: Empty items list but totalItems > 0
        if fetched_count == 0 and current_total_estimate > 0:
            print(f"      ⚠️ API Bug: Empty page. Attempting rescue with maxResults={current_total_estimate}...")
            rescue_url = f'https://www.googleapis.com/books/v1/volumes?q=inauthor:"{encoded_name}"&maxResults={current_total_estimate}&startIndex={start_index}&key={API_KEY}'
            request_urls.append(rescue_url)
            
            try:
                rescue_response = requests.get(rescue_url, timeout=30)
                rescue_data = rescue_response.json()
                rescue_items = rescue_data.get('items', [])
                
                if rescue_items:
                    print(f"      ✓ Rescue successful, added {len(rescue_items)} items.")
                    all_items.extend(rescue_items)
            except requests.exceptions.RequestException as e:
                print(f"      ✗ Rescue request also failed: {e}")
            break  # Stop after rescue attempt
        
        # NORMAL CASE: Items received
        if fetched_count > 0:
            all_items.extend(current_items)
        
        # TERMINATION RULE 2: Natural end (partial page)
        if fetched_count < BATCH_SIZE:
            break
        
        # Prepare for next page
        start_index += BATCH_SIZE
        time.sleep(DELAY_BETWEEN_PAGES)  # Small delay between pages
    
    # Compile final result for this author
    final_data = {
        "getRequest": first_request_url,
        "_requestUrls": request_urls,
        "_totalQueriedItems": initial_total_estimate,
        "_totalFetchedItems": len(all_items),
        "_totalRequestsMade": request_count,
        "_batchSizeUsed": BATCH_SIZE,
        "items": all_items
    }
    
    print(f"   ✓ Finished. Fetched {len(all_items)} items from {request_count} requests.")
    return safe_name, author_viaf, final_data

# ================= MAIN PROCESSING LOOP =================
print("\n" + "="*60)
print("STARTING BATCH PROCESSING OF ALL AUTHORS")
print("="*60)

for idx, author_entry in enumerate(all_authors):
    try:
        author_name = author_entry['authorLabel']['value']
        author_viaf = author_entry.get('viaf', {}).get('value', f'NO_VIAF_{idx}')
        date_of_death = author_entry.get('date_of_death', {}).get('value', '')
    except KeyError as e:
        print(f"\n⏭️ Skipping entry {idx}: Missing key {e} in data.")
        continue
    
    print(f"\n[{idx+1}/{len(all_authors)}] Processing: {author_name} (VIAF: {author_viaf})")
    
    # Fetch all data for this author
    safe_name, viaf, author_result_data = fetch_all_books_for_author(author_name, author_viaf)
    
    # Save individual consolidated JSON file
    filename = f"{safe_name}-{viaf}-CONSOLIDATED.json"
    filepath = os.path.join(OUTPUT_BASE_DIR, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(author_result_data, f, indent=2, ensure_ascii=False)
        print(f"   💾 Saved to: {filename}")
    except IOError as e:
        print(f"   ❌ Failed to save file: {e}")
        # Continue processing other authors even if save fails
    
    # Update summary
    summary_data["authorsProcessed"].append({
        "authorLabel": author_name,
        "viaf": viaf,
        "dateOfDeath": date_of_death,
        "outputFile": filename,
        "totalQueried": author_result_data["_totalQueriedItems"],
        "totalFetched": author_result_data["_totalFetchedItems"],
        "requestsMade": author_result_data["_totalRequestsMade"]
    })
    
    # Write running log
    with open(log_file_path, 'a', encoding='utf-8') as log:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log.write(f"{timestamp} | {author_name} | {author_result_data['_totalFetchedItems']} items | {filename}\n")
    
    # Delay before next author (unless it's the last one)
    if idx < len(all_authors) - 1:
        print(f"   ⏳ Waiting {DELAY_BETWEEN_AUTHORS} seconds before next author...")
        time.sleep(DELAY_BETWEEN_AUTHORS)

# ================= FINAL SUMMARY =================
print("\n" + "="*60)
print("PROCESSING COMPLETE")
print("="*60)

# Save master summary file
summary_filename = os.path.join(OUTPUT_BASE_DIR, "_processing_summary.json")
try:
    with open(summary_filename, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)
    print(f"📊 Master summary saved to: {summary_filename}")
except IOError as e:
    print(f"   ❌ Failed to save summary file: {e}")

# Print final stats
successful = [a for a in summary_data["authorsProcessed"] if a["totalFetched"] > 0]
print(f"\n📈 Results:")
print(f"   • Total authors processed: {len(summary_data['authorsProcessed'])}")
print(f"   • Authors with results: {len(successful)}")
print(f"   • Total books fetched: {sum(a['totalFetched'] for a in summary_data['authorsProcessed'])}")
print(f"   • Detailed log: {log_file_path}")
print("="*60)