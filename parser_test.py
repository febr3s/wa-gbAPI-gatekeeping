import json
import csv
import re
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
    
    def create_title_slug(self, title: str) -> str:
        """Convert title to a slug for the PDF URL."""
        if not title:
            return ""
        
        # Convert to lowercase
        slug = title.lower()
        
        # Replace spaces with underscores
        slug = slug.replace(' ', '_')
        
        # Remove or replace special characters
        slug = re.sub(r'[^\w\s-]', '', slug)  # Remove non-alphanumeric except spaces and hyphens
        slug = re.sub(r'[-\s]+', '_', slug)   # Replace spaces and multiple hyphens with underscore
        
        # Remove leading/trailing underscores
        slug = slug.strip('_')
        
        # Limit length (optional, but good for URLs)
        if len(slug) > 100:
            slug = slug[:100]
        
        return slug
    
    def get_url(self, item: Dict) -> str:
        """Get URL based on availability."""
        volume_info = item.get('volumeInfo', {})
        access_info = item.get('accessInfo', {})
        sale_info = item.get('saleInfo', {})
        
        # Get volume ID
        volume_id = item.get('id', '')
        
        # Check if PDF is available AND has downloadLink
        pdf_info = access_info.get('pdf', {})
        pdf_available = pdf_info.get('isAvailable', False)
        has_download_link = 'downloadLink' in pdf_info
        
        # Check saleability
        saleability = sale_info.get('saleability', '')
        is_free = saleability.upper() == 'FREE'
        
        # Case 1: PDF available with downloadLink
        if pdf_available and has_download_link:
            return pdf_info.get('downloadLink', '')
        
        # Case 2: PDF is FALSE but saleability is FREE - compose special URL
        elif not pdf_available and is_free:
            title = volume_info.get('title', '')
            title_slug = self.create_title_slug(title)
            
            if title_slug and volume_id:
                return f"https://books.google.com/books/download/{title_slug}.pdf?id={volume_id}&output=pdf"
            else:
                # Fallback to buyLink or infoLink
                return sale_info.get('buyLink', volume_info.get('infoLink', ''))
        
        # Case 3: Shouldn't reach here if filtering is correct, but provide fallback
        return volume_info.get('infoLink', '')
    
    def should_include_item(self, item: Dict, debug: bool = False) -> bool:
        """Check if item meets inclusion criteria."""
        access_info = item.get('accessInfo', {})
        sale_info = item.get('saleInfo', {})
        
        # Check condition 1: PDF is available AND has downloadLink
        pdf_info = access_info.get('pdf', {})
        pdf_available = pdf_info.get('isAvailable', False)
        has_download_link = 'downloadLink' in pdf_info
        
        # Check condition 2: Saleability is FREE
        saleability = sale_info.get('saleability', '')
        is_free = saleability.upper() == 'FREE'
        
        if debug:
            print(f"  PDF isAvailable: {pdf_available}")
            print(f"  Has downloadLink: {has_download_link}")
            print(f"  Saleability: '{saleability}'")
            print(f"  Is FREE: {is_free}")
            print(f"  Should include: {(pdf_available and has_download_link) or is_free}")
        
        # Include item if: (PDF available AND has downloadLink) OR (saleability is FREE)
        return (pdf_available and has_download_link) or is_free
    
    def is_match(self, item: Dict, debug: bool = False) -> bool:
        """
        Check if item is a match - author must contain "Francisco de Miranda".
        Other authors can also be present.
        """
        volume_info = item.get('volumeInfo', {})
        authors = volume_info.get('authors', [])
        
        # Check if "Francisco de Miranda" is in the authors list
        is_match = "Francisco de Miranda" in authors
        
        if debug:
            print(f"  Authors: {authors}")
            print(f"  Contains 'Francisco de Miranda': {is_match}")
        
        return is_match
    
    def parse_item(self, item: Dict, index: int) -> Dict[str, str]:
        """Parse a single Google Books item to Zotero format."""
        volume_info = item.get('volumeInfo', {})
        
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
            "Abstract Note": "",
            "Date": year,
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
            "Notes": volume_info.get('description', ''),
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
    
    def parse_json_to_csv(self, json_file_path: str, matches_csv_path: str, non_matches_csv_path: str, debug: bool = False):
        """Main function to parse JSON file and create two CSV outputs."""
        # Read JSON file
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Parse all items, filtering by criteria
        items = data.get('items', [])
        matches_records = []
        non_matches_records = []
        excluded_count = 0
        
        for i, item in enumerate(items):
            try:
                title = item.get('volumeInfo', {}).get('title', f'Item {i}')
                
                if debug:
                    print(f"\nChecking item {i}: {title}")
                
                # First check: Does it meet inclusion criteria?
                include_item = self.should_include_item(item, debug)
                
                if include_item:
                    # Second check: Is it a match?
                    is_a_match = self.is_match(item, debug)
                    
                    record = self.parse_item(item, i)
                    
                    if debug:
                        access_info = item.get('accessInfo', {})
                        pdf_info = access_info.get('pdf', {})
                        sale_info = item.get('saleInfo', {})
                        print(f"  PDF available with downloadLink: {pdf_info.get('isAvailable', False) and 'downloadLink' in pdf_info}")
                        print(f"  Saleability FREE: {sale_info.get('saleability', '').upper() == 'FREE'}")
                        print(f"  Selected URL: {record['Url'][:100]}..." if len(record['Url']) > 100 else f"  Selected URL: {record['Url']}")
                    
                    # Categorize based on match status
                    if is_a_match:
                        matches_records.append(record)
                        if debug:
                            print(f"  → ADDED TO MATCHES")
                    else:
                        non_matches_records.append(record)
                        if debug:
                            print(f"  → ADDED TO NON-MATCHES")
                else:
                    if debug:
                        print(f"  → EXCLUDED - Doesn't meet inclusion criteria")
                    excluded_count += 1
            except Exception as e:
                print(f"Error parsing item {i}: {e}")
                excluded_count += 1
                continue
        
        # Write matches to CSV
        with open(matches_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.csv_headers, 
                                   quoting=csv.QUOTE_ALL, 
                                   quotechar='"')
            writer.writeheader()
            writer.writerows(matches_records)
        
        # Write non-matches to CSV
        with open(non_matches_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.csv_headers, 
                                   quoting=csv.QUOTE_ALL, 
                                   quotechar='"')
            writer.writeheader()
            writer.writerows(non_matches_records)
        
        print(f"\n=== SUMMARY ===")
        print(f"Matches: {len(matches_records)} items → {matches_csv_path}")
        print(f"Non-matches: {len(non_matches_records)} items → {non_matches_csv_path}")
        print(f"Excluded: {excluded_count} items (didn't meet inclusion criteria)")
        return len(matches_records), len(non_matches_records)


# Usage example
if __name__ == "__main__":
    parser = GoogleBooksToZoteroParser()
    
    # Example usage - add debug=True to see what's happening
    input_json = "raw_gbooks_data/Francisco_de_Miranda-27068875-CONSOLIDATED.json"
    matches_csv = "matches_output.csv"
    non_matches_csv = "non_matches_output.csv"
    
    # Parse the data with debugging
    match_count, non_match_count = parser.parse_json_to_csv(
        input_json, matches_csv, non_matches_csv, debug=True
    )
    print(f"Processed {match_count} matches and {non_match_count} non-matches")