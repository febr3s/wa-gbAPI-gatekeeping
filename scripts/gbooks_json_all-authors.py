import os
import glob
import requests
import json
import time
from urllib.parse import quote
from datetime import datetime

def get_query_origin():
    """Return dict with public IP and location info, or an error message."""
    try:
        resp = requests.get("https://ipinfo.io/json", timeout=5)
        resp.raise_for_status()
        return resp.json()   # contains ip, city, region, country, loc, org
    except Exception as e:
        return {"error": f"Could not determine origin: {e}"}

# ================= CONFIGURATION =================
API_KEY = os.environ.get('GOOGLE_BOOKS_API_KEY')
COUNTRY_ABBREV = "NIC"  # 3-letter ISO code for the country, used in output paths
INPUT_JSON_PATTERN = f'output/{COUNTRY_ABBREV}/authors_{COUNTRY_ABBREV}_*.json'
OUTPUT_BASE_DIR = f'output/{COUNTRY_ABBREV}'
DELAY_BETWEEN_AUTHORS = 5
DELAY_BETWEEN_PAGES = 0.3
BATCH_SIZE = 20
RETRY_DELAY_SECONDS = 5      # Wait this long before retrying a 503
MAX_RETRIES = 3              # Maximum retries per request

# ================= SETUP =================
if not API_KEY:
    print("ERROR: Set the 'GOOGLE_BOOKS_API_KEY' environment variable first.")
    exit()
    
# ---- Determine query origin IP & location ----
query_origin = get_query_origin()
origin_country = query_origin.get("country", "unknown")

# ---- Load the most recent author data file matching the pattern ----
matching_files = glob.glob(INPUT_JSON_PATTERN)
if not matching_files:
    print(f"ERROR: No files found matching '{INPUT_JSON_PATTERN}'")
    exit()

input_file = max(matching_files, key=os.path.getmtime)

try:
    with open(input_file, 'r', encoding='utf-8') as f:
        author_data = json.load(f)
    all_authors = author_data['results']['bindings']
    print(f"📚 Loaded data for {len(all_authors)} authors from {os.path.basename(input_file)}")
except (KeyError, FileNotFoundError, json.JSONDecodeError) as e:
    print(f"ERROR: Could not load or parse '{input_file}': {e}")
    exit()

# Prepare logs and summary
log_file_path = os.path.join(OUTPUT_BASE_DIR, f"run_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

# Write origin info as the log’s first line (once, before the loop)
with open(log_file_path, 'w', encoding='utf-8') as log:
    ip = query_origin.get("ip", "unknown")
    city = query_origin.get("city", "unknown")
    country = query_origin.get("country", "unknown")
    log.write(f"Query origin: IP {ip} ({city}, {country})\n")

summary_data = {
    "scriptRunTimestamp": datetime.now().isoformat(),
    "_queryOrigin": query_origin,
    "totalAuthorsQueried": len(all_authors),
    "authorsProcessed": [],
    "_config": {
        "delayBetweenAuthors": DELAY_BETWEEN_AUTHORS,
        "delayBetweenPages": DELAY_BETWEEN_PAGES,
        "batchSize": BATCH_SIZE,
        "retryDelaySeconds": RETRY_DELAY_SECONDS,
        "maxRetries": MAX_RETRIES
    }
}

# ================= CORE PAGINATION FUNCTION =================
def fetch_all_books_for_author(author_name, author_viaf):
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
        
        current_url = f'https://www.googleapis.com/books/v1/volumes?q=inauthor:"{encoded_name}"&maxResults={BATCH_SIZE}&startIndex={start_index}&key={API_KEY}'
        request_urls.append(current_url)
        
        if first_request_url is None:
            first_request_url = current_url
        
        # --- REQUEST WITH RETRY FOR 503 ---
        retry_count = 0
        response = None
        while retry_count <= MAX_RETRIES:
            try:
                response = requests.get(current_url, timeout=30)
                if response.status_code == 503:
                    retry_count += 1
                    if retry_count <= MAX_RETRIES:
                        print(f"      ⚠️ Got 503, waiting {RETRY_DELAY_SECONDS}s (attempt {retry_count}/{MAX_RETRIES})...")
                        time.sleep(RETRY_DELAY_SECONDS)
                        continue
                    else:
                        print(f"      ✗ Max retries exceeded after {MAX_RETRIES} attempts.")
                        break
                else:
                    response.raise_for_status()      # Raise for any other HTTP error
                    break                            # Success – exit retry loop
            except requests.exceptions.RequestException as e:
                print(f"      ⚠️ Request #{request_count} failed: {e}")
                break   # Non‑recoverable error → stop pagination
        if response is None or response.status_code != 200:
            break   # Pagination stops for this author
        current_data = response.json()
        # ------------------------------------
        
        current_total_estimate = current_data.get('totalItems', 0)
        current_items = current_data.get('items', [])
        fetched_count = len(current_items)
        
        if request_count == 1:
            initial_total_estimate = current_total_estimate
        
        if current_total_estimate == 0:
            print(f"      No results found (totalItems=0).")
            break
        
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
            break
        
        if fetched_count > 0:
            all_items.extend(current_items)
        
        if fetched_count < BATCH_SIZE:
            break
        
        start_index += BATCH_SIZE
        time.sleep(DELAY_BETWEEN_PAGES)
    
    # Redact API key before storing URLs
    first_request_url = first_request_url.replace(API_KEY, "REDACTED") if first_request_url else None
    request_urls = [url.replace(API_KEY, "REDACTED") for url in request_urls]

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
    
    safe_name, viaf, author_result_data = fetch_all_books_for_author(author_name, author_viaf)
    
    filename = f"{safe_name}-{viaf}-CONSOLIDATED.json"
    filepath = os.path.join(OUTPUT_BASE_DIR, "raw_data", f"from_{origin_country}", filename)
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(author_result_data, f, indent=2, ensure_ascii=False)
        print(f"   💾 Saved to: {filename}")
    except IOError as e:
        print(f"   ❌ Failed to save file: {e}")
    
    summary_data["authorsProcessed"].append({
        "authorLabel": author_name,
        "viaf": viaf,
        "dateOfDeath": date_of_death,
        "outputFile": filename,
        "totalQueried": author_result_data["_totalQueriedItems"],
        "totalFetched": author_result_data["_totalFetchedItems"],
        "requestsMade": author_result_data["_totalRequestsMade"]
    })
    
    with open(log_file_path, 'a', encoding='utf-8') as log:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log.write(f"{timestamp} | {author_name} | {author_result_data['_totalFetchedItems']} items | {filename}\n")
    
    if idx < len(all_authors) - 1:
        print(f"   ⏳ Waiting {DELAY_BETWEEN_AUTHORS} seconds before next author...")
        time.sleep(DELAY_BETWEEN_AUTHORS)

# ================= FINAL SUMMARY =================
print("\n" + "="*60)
print("PROCESSING COMPLETE")
print("="*60)

summary_filename = os.path.join(OUTPUT_BASE_DIR, f"{COUNTRY_ABBREV}_query_report_{origin_country}.json")
try:
    with open(summary_filename, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)
    print(f"📊 Master summary saved to: {summary_filename}")
except IOError as e:
    print(f"   ❌ Failed to save summary file: {e}")

successful = [a for a in summary_data["authorsProcessed"] if a["totalFetched"] > 0]
print(f"\n📈 Results:")
print(f"   • Total authors processed: {len(summary_data['authorsProcessed'])}")
print(f"   • Authors with results: {len(successful)}")
print(f"   • Total books fetched: {sum(a['totalFetched'] for a in summary_data['authorsProcessed'])}")
print(f"   • Detailed log: {log_file_path}")
print("="*60)