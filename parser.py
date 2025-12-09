import json
import csv
from datetime import datetime
from typing import List, Dict, Any

class GoogleBooksToZoteroParser:
    def __init__(self):
        self.csv_headers = [
            "Key", "Item Type", "Publication Year", "Author", "Title", "Publication Title",
            "ISBN", "ISSN", "DOI", "Url", "Abstract Note", "Date", "Date Added", 
            "Date Modified", "Access Date", "Pages", "Num Pages", "Issue", "Volume", 
            "Number Of Volumes", "Journal Abbreviation", "Short Title", "Series", 
            "Series Number", "Series Text", "Series Title", "Publisher", "Place", 
            "Language", "Rights", "Type", "Archive", "Archive Location", "Library Catalog", 
            "Call Number", "Extra", "Notes", "File Attachments", "Link Attachments", 
            "Manual Tags", "Automatic Tags", "Editor", "Series Editor", "Translator", 
            "Contributor", "Attorney Agent", "Book Author", "Cast Member", "Commenter", 
            "Composer", "Cosponsor", "Counsel", "Interviewer", "Producer", "Recipient", 
            "Reviewed Author", "Scriptwriter", "Words By", "Guest", "Number", "Edition", 
            "Running Time", "Scale", "Medium", "Artwork Size", "Filing Date", 
            "Application Number", "Assignee", "Issuing Authority", "Country", 
            "Meeting Name", "Conference Name", "Court", "References", "Reporter", 
            "Legal Status", "Priority Numbers", "Programming Language", "Version", 
            "System", "Code", "Code Number", "Section", "Session", "Committee", 
            "History", "Legislative Body"
        ]
        
    def format_authors(self, authors: List[str]) -> str:
        """Convert author names from 'First Last' to 'Last, First' format."""
        if not authors:
            return ""
        
        formatted = []
        for author in authors:
            # Handle cases like "Díaz Sánchez, Ramón" (already formatted)
            if ', ' in author:
                formatted.append(author)
            else:
                # Split by spaces and assume last word is last name
                parts = author.split()
                if len(parts) >= 2:
                    last_name = parts[-1]
                    first_names = ' '.join(parts[:-1])
                    formatted.append(f"{last_name}, {first_names}")
                else:
                    formatted.append(author)
        
        return '; '.join(formatted)
    
    def extract_isbn(self, industry_identifiers: List[Dict]) -> str:
        """Extract ISBN from industry identifiers."""
        if not industry_identifiers:
            return ""
        
        # Prefer ISBN_13, fall back to ISBN_10
        isbn_13 = None
        isbn_10 = None
        
        for identifier in industry_identifiers:
            if identifier.get('type') == 'ISBN_13':
                isbn_13 = identifier.get('identifier', '')
            elif identifier.get('type') == 'ISBN_10':
                isbn_10 = identifier.get('identifier', '')
        
        return isbn_13 or isbn_10 or ""
    
    def extract_year(self, published_date: str) -> str:
        """Extract year from publishedDate."""
        if not published_date:
            return ""
        
        # Try to extract year from date string
        try:
            # Handle formats like "1969", "2004-01", "2004-01-15"
            year_part = published_date.split('-')[0]
            if year_part.isdigit() and len(year_part) == 4:
                return year_part
        except:
            pass
        
        return ""
    
    def get_url(self, item: Dict) -> str:
        """Get URL from pdf downloadLink or infoLink."""
        volume_info = item.get('volumeInfo', {})
        access_info = item.get('accessInfo', {})
        
        # Check if PDF is available
        pdf_info = access_info.get('pdf', {})
        if pdf_info.get('isAvailable') and 'downloadLink' in pdf_info:
            return pdf_info.get('downloadLink', '')
        
        # Fall back to infoLink
        return volume_info.get('infoLink', '')
    
    def parse_item(self, item: Dict, index: int) -> Dict[str, str]:
        """Parse a single Google Books item to Zotero format."""
        volume_info = item.get('volumeInfo', {})
        access_info = item.get('accessInfo', {})
        
        # Format title with subtitle
        title = volume_info.get('title', '')
        subtitle = volume_info.get('subtitle', '')
        if subtitle:
            full_title = f"{title}: {subtitle}"
        else:
            full_title = title
        
        # Extract year from publishedDate
        published_date = volume_info.get('publishedDate', '')
        year = self.extract_year(published_date)
        
        # Get current timestamp for Date Added/Modified
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create the Zotero record
        record = {
            "Key": "",  # Empty as requested
            "Item Type": "book",
            "Publication Year": year,
            "Author": self.format_authors(volume_info.get('authors', [])),
            "Title": full_title,
            "Publication Title": "",
            "ISBN": self.extract_isbn(volume_info.get('industryIdentifiers', [])),
            "ISSN": "",
            "DOI": "",
            "Url": self.get_url(item),
            "Abstract Note": volume_info.get('description', ''),
            "Date": year,  # Only year for Date field
            "Date Added": current_time,
            "Date Modified": current_time,
            "Access Date": "",
            "Pages": "",
            "Num Pages": str(volume_info.get('pageCount', '')),
            "Issue": "",
            "Volume": "",
            "Number Of Volumes": "",
            "Journal Abbreviation": "",
            "Short Title": "",
            "Series": "",
            "Series Number": "",
            "Series Text": "",
            "Series Title": "",
            "Publisher": volume_info.get('publisher', ''),
            "Place": "",
            "Language": volume_info.get('language', ''),
            "Rights": "",
            "Type": "",
            "Archive": "Google Books",
            "Archive Location": "",
            "Library Catalog": "",
            "Call Number": "",
            "Extra": "Venezuela",
            "Notes": "",
            "File Attachments": volume_info.get('imageLinks', {}).get('thumbnail', ''),
            "Link Attachments": "",
            "Manual Tags": "",
            "Automatic Tags": "",
            "Editor": "",
            "Series Editor": "",
            "Translator": "",
            "Contributor": "",
            "Attorney Agent": "",
            "Book Author": "",
            "Cast Member": "",
            "Commenter": "",
            "Composer": "",
            "Cosponsor": "",
            "Counsel": "",
            "Interviewer": "",
            "Producer": "",
            "Recipient": "",
            "Reviewed Author": "",
            "Scriptwriter": "",
            "Words By": "",
            "Guest": "",
            "Number": "",
            "Edition": "",
            "Running Time": "",
            "Scale": "",
            "Medium": "",
            "Artwork Size": "",
            "Filing Date": "",
            "Application Number": "",
            "Assignee": "",
            "Issuing Authority": "",
            "Country": "",
            "Meeting Name": "",
            "Conference Name": "",
            "Court": "",
            "References": "",
            "Reporter": "",
            "Legal Status": "",
            "Priority Numbers": "",
            "Programming Language": "",
            "Version": "",
            "System": "",
            "Code": "",
            "Code Number": "",
            "Section": "",
            "Session": "",
            "Committee": "",
            "History": "",
            "Legislative Body": ""
        }
        
        return record
    
    def parse_json_to_csv(self, json_file_path: str, csv_file_path: str):
        """Main function to parse JSON file and create CSV output."""
        # Read JSON file
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Parse all items
        items = data.get('items', [])
        records = []
        
        for i, item in enumerate(items):
            try:
                record = self.parse_item(item, i)
                records.append(record)
            except Exception as e:
                print(f"Error parsing item {i}: {e}")
                continue
        
        # Write to CSV with quoting to match the model
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as f:
            # Use QUOTE_ALL to quote all fields
            writer = csv.DictWriter(f, fieldnames=self.csv_headers, 
                                   quoting=csv.QUOTE_ALL, 
                                   quotechar='"')
            writer.writeheader()
            writer.writerows(records)
        
        print(f"Successfully parsed {len(records)} items to {csv_file_path}")
        return len(records)


# Usage example
if __name__ == "__main__":
    parser = GoogleBooksToZoteroParser()
    
    # Example usage
    input_json = "raw_gbooks_data/Francisco_de_Miranda-27068875-CONSOLIDATED.json"
    output_csv = "zotero_output.csv"
    
    # Parse the data
    count = parser.parse_json_to_csv(input_json, output_csv)
    print(f"Processed {count} records")