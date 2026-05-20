import os
import requests

COUNTRY_ABBREV = "HND"  # 3-letter ISO code for the country, used in output paths
INPUT_JSON_PATTERN = f'output/{COUNTRY_ABBREV}/authors_{COUNTRY_ABBREV}_*.json'
OUTPUT_BASE_DIR = f'output/{COUNTRY_ABBREV}'

def get_query_origin():
    """Return dict with public IP and location info, or an error message."""
    try:
        resp = requests.get("https://ipinfo.io/json", timeout=5)
        resp.raise_for_status()
        return resp.json()   # contains ip, city, region, country, loc, org
    except Exception as e:
        return {"error": f"Could not determine origin: {e}"}

# ---- Determine query origin IP & location ----
query_origin = get_query_origin()
origin_country = query_origin.get("country", "unknown")


# ================= CONCAT INTO ONE FILE =================
import subprocess
import glob as glob_mod  # avoid conflict with existing glob import

raw_data_dir = os.path.join(OUTPUT_BASE_DIR, "raw_data", f"from_{origin_country}")
combined_file = os.path.join(OUTPUT_BASE_DIR, f"{COUNTRY_ABBREV}_books_from_{origin_country}.json")

# Collect all JSON files from the directory
json_files = sorted(glob_mod.glob(os.path.join(raw_data_dir, "*.json")))

if json_files:
    # Build jq command: slurp all files into one JSON array
    # The -s (--slurp) flag reads each file and places its content into an array.
    cmd = ["jq", "-s", "."] + json_files

    try:
        with open(combined_file, 'w', encoding='utf-8') as out_f:
            subprocess.run(cmd, stdout=out_f, check=True, text=True)
        print(f"📚 Combined {len(json_files)} files into: {combined_file}")
    except subprocess.CalledProcessError as e:
        print(f"❌ jq failed with error: {e}")
    except FileNotFoundError:
        print("❌ 'jq' command not found. Please install jq or adjust PATH.")
else:
    print("⚠️ No JSON files found to combine.")


