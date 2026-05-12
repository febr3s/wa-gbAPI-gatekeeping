# wa-gbAPI-gatekeeping

A Python toolkit to extract, filter, and prepare public domain book records from Google Books for a specific country, then export them for Zotero and static website generation.

This workflow helps you build a clean dataset of freely downloadable PDF books that are in the public domain according to the copyright laws of your target country. It uses Wikidata to fetch authors of a given nationality and death date, queries the Google Books API for their works, and filters results to include only those with PDF downloads. The final output is a CSV ready for import into Zotero and compatible with the [MOREL](https://github.com/febr3s/morel) static site generator.

## Prerequisites

- Python 3.6 or higher
- A Google Books API key (see [Google Cloud Console](https://console.cloud.google.com/))
- Basic familiarity with the command line

## Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/febr3s/wa-gbAPI-gatekeeping.git
   cd wa-gbAPI-gatekeeping
   ```

2. **Install required Python packages:**
   ```bash
   pip install -r requirements.txt
   ```
   *(If `requirements.txt` is missing, install `requests` and any other dependencies manually.)*

3. **Set your Google Books API key as an environment variable:**
   ```bash
   export GOOGLE_BOOKS_API_KEY="YOUR_API_KEY_HERE"
   ```
   (On Windows use `set GOOGLE_BOOKS_API_KEY=YOUR_API_KEY_HERE`)

4. **Prepare country‑specific parameters:**
   Before running the scripts, you must edit `wikidata.py` to define the country and the copyright cutoff year.

## Step‑by‑Step Usage

### Step 1: Fetch authors from Wikidata

Run `wikidata.py`. **Important:** You **must** edit the following lines inside the script to match your target country and its public domain rules:

```python
# Example for Venezuela (Q717) with a 60-year post‑mortem term (death before 1965 for 2025)
query = """
SELECT ?author ?authorLabel ?date_of_death WHERE {
  ?author wdt:P27 wd:Q717 .   # <-- Change Q717 to your country's Wikidata ID
  ?author wdt:P570 ?date_of_death .
  FILTER(?date_of_death < "1965-01-01"^^xsd:dateTime)   # <-- Adjust the date
}
"""
```

Also update the output filename (e.g., `venezuelan_authors.json` → `german_authors.json`).

**What this does:**  
Queries Wikidata for authors with citizenship `wd:Q717` (Venezuela) who died before January 1, 1965. The resulting JSON file lists all authors and their death dates.

> **You are here:** You now have a file listing all authors of the selected nationality who died before the legal cutoff year. Public domain status is determined by your country's copyright term (e.g., life + 70 years for EU, life + 60 for Venezuela).

---

### Step 2: Query Google Books for each author

Run `gbooks_json_all-authors.py`. If you changed the country in Step 1, update the `INPUT_JSON_FILE` variable at the top of the script to match the filename you used.

```python
INPUT_JSON_FILE = "venezuelan_authors.json"   # Change to your file
```

**What this does:**  
For every author in the JSON file, the script calls the Google Books API and saves all book records found. Each author gets its own mini‑dataset saved as `data/[author_name].json`.

> **You are here:** You now have a folder `data/` containing one JSON file per author, each with a complete list of their books found in Google Books.

---

### Step 3: Parse and filter for downloadable PDFs

Run `parser.py`.

**What this does:**  
The script scans every `raw_gobooks_data/*.json` file and extracts books that have a downloadable PDF link. It then applies a nationality check (based on Wikidata data) to separate likely matches from likely mismatches:

- **`consolidated_matches.csv`** – Books that appear to be by an author of the target nationality.
- **`consolidated_non_matches.csv`** – Books that have a PDF but the metadata suggests the author might not match (e.g., a different person with the same name).

> **You are here:** Two CSV files are created. They contain the raw candidate records for manual review.

---

### Step 4: Review matches and clean false positives

Open `consolidated_matches.csv` in a spreadsheet editor or text editor.

- Delete rows that are **false positives** (e.g., a different author with the same name who is still in copyright).
- **Tip:** Keep notes of incorrect nationality claims; you can later fix them on Wikidata.

---

### Step 5: Review non‑matches and rescue false negatives

Open `consolidated_non_matches.csv`.

- Sometimes Google Books metadata is incomplete or wrong, causing a legitimate public‑domain book to be classified as a non‑match.
- Delete rows that are **true negatives** (books that really should not be included).
- Keep rows that are actually valid public‑domain books by your target authors.

---

### Step 6: Merge the two CSV files

Combine the remaining rows from both files into a single CSV named `consolidated_all_pdf_matches.csv`.

You can do this via the command line:

```bash
cat consolidated_matches.csv consolidated_non_matches.csv > consolidated_all_pdf_matches.csv
```

Or simply copy and paste the data in a spreadsheet editor.

> **You are here:** You now have a clean, curated dataset of all public‑domain books (with PDF downloads) for the chosen country, ready for import into reference management software.

---

### Step 7: Convert to Zotero‑compatible CSV

Run `parser_to_zotero.py`.

**What this does:**  
Reads `consolidated_all_pdf_matches.csv` and outputs a new CSV file formatted specifically for Zotero import. The fields are mapped to Zotero's required columns (Title, Author, Date, URL, etc.).

> **You are here:** The resulting file (`zotero_import.csv`) can be directly imported into Zotero to create a library of public domain works, complete with PDF links.

---

### Step 8: Import into Zotero

1. Open Zotero.
2. Go to **File → Import…**.
3. Select the CSV file generated in Step 7.
4. Follow the import wizard, mapping the columns as prompted.

After import, you will have a Zotero collection of all public domain books, each with a link to its Google Books PDF. Zotero can also be used to download the PDFs locally.

---

### Step 9: Generate a website with MOREL

The final dataset is compatible with [MOREL](https://github.com/febr3s/morel), a static site generator for digital libraries. Export your Zotero collection as CSL JSON and feed it to MOREL to create a browsable, searchable website of public domain books.

---

## Customization Notes

- **Changing the country:** Replace the Wikidata ID (`wd:Q717`) and adjust the death date filter in `wikidata.py`.
- **Changing the copyright term:** Modify the `FILTER(?date_of_death < "YYYY-MM-DD"^^xsd:dateTime)` line.
- **API rate limits:** The Google Books API has a daily quota. The scripts include a small delay between requests to avoid hitting limits. If you have a large author list, consider running `gbooks_json_all-authors.py` in batches.

## Troubleshooting

- **No API key found:** Ensure the environment variable `GOOGLE_BOOKS_API_KEY` is set correctly.
- **Empty author list:** Check that the Wikidata query in `wikidata.py` returns results. You can test it at [query.wikidata.org](https://query.wikidata.org/).
- **Missing `data/` folder:** `gbooks_json_all-authors.py` creates it automatically. If you run `parser.py` first, you may get an error; just create the folder manually or run Step 2 first.

## License

This project is released under the MIT License. See [LICENSE](LICENSE) for details.