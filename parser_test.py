import json
import csv
import os
import re
import urllib.parse
from datetime import datetime
from typing import List, Dict, Any, Tuple

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
        
    def extract_author_from_url(self, url: str) -> str:
        """
        Extract author name from Google Books API URL.
        Example: https://www.googleapis.com/books/v1/volumes?q=inauthor:"Francisco%20de%20Miranda"
        Returns: "Francisco de Miranda"
        """
        if not url:
            return ""
        
        try:
            # Parse the URL
            parsed = urllib.parse.urlparse(url)
            query_params = urllib.parse.parse_qs(parsed.query)
            
            # Get the 'q' parameter
            q_param = query_params.get('q', [''])[0]
            
            # Extract author from inauthor:"Author Name"
            match = re.search(r'inauthor:"([^"]+)"', q_param)
            if match:
                author_encoded = match.group(1)
                # Decode URL encoding (e.g., %20 -> space)
                author_decoded = urllib.parse.unquote(author_encoded)
                return author_decoded
            
        except Exception as e:
            print(f"Error extracting author from URL: {e}")
        
        return ""
    
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
    
    def get_image_links(self, image_links: Dict) -> str:
        """Get the best available image link from imageLinks object."""
        if not image_links:
            return ""
        
        # Prefer higher quality images in this order
        image_priorities = [
            'extraLarge',
            'large',
            'medium',
            'small',
            'thumbnail',
            'smallThumbnail'
        ]
        
        for priority in image_priorities:
            if priority in image_links and image_links[priority]:
                return image_links[priority]
        
        return ""
    
    def clean_html_from_description(self, description: str) -> str:
        """Remove HTML tags from description if present."""
        if not description:
            return ""
        
        # Simple HTML tag removal (can be enhanced if needed)
        clean_text = re.sub(r'<[^>]+>', '', description)
        # Replace HTML entities
        clean_text = clean_text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&#39;', "'")
        # Clean up multiple spaces and newlines
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        return clean_text
    
    def should_include_item(self, item: Dict, debug: bool = True ) -> bool:
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
    
    def is_match(self, item: Dict, target_author: str, debug: bool = False) -> bool:
        """
        Check if item is a match - author must contain the target author name.
        Other authors can also be present.
        """
        volume_info = item.get('volumeInfo', {})
        authors = volume_info.get('authors', [])
        
        # If no target_author is specified, everything is a match
        if not target_author:
            return True
        
        # Check if the target_author is in the authors list
        is_match = target_author in authors
        
        if debug:
            print(f"  Authors: {authors}")
            print(f"  Contains '{target_author}': {is_match}")
        
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
        
        # Extract Publisher
        publisher = volume_info.get('publisher', '')
        
        # Extract and clean Notes (description)
        description = volume_info.get('description', '')
        notes = self.clean_html_from_description(description)
        
        # Extract image links for attachments
        image_links = volume_info.get('imageLinks', {})
        file_attachments = self.get_image_links(image_links)
        
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
            "Publisher": publisher,  # Fixed: Now properly using publisher variable
            "Place": "",
            "Language": volume_info.get('language', ''),
            "Rights": "",
            "Type": "",
            "Archive": "Google Books",
            "Archive Location": "",
            "Library Catalog": "",
            "Call Number": "",
            "Extra": "Venezuela",
            "Notes": notes,  # Fixed: Now using cleaned description
            "File Attachments": file_attachments,  # Fixed: Now using best available image link
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
        
        # Debug output for the three fields
        debug_output = False
        if debug_output:
            print(f"\nDebug for item {index}:")
            print(f"  Title: {full_title}")
            print(f"  Publisher: '{publisher}'")
            print(f"  Notes (first 100 chars): '{notes[:100]}...'")
            print(f"  File Attachments (image): '{file_attachments}'")
        
        return record
    
    def parse_json_file(self, json_file_path: str, debug: bool = False) -> Tuple[List[Dict], List[Dict], int, str]:
        """
        Parse a single JSON file and return matches, non-matches, excluded count, and detected author.
        """
        # Read JSON file
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract author from the getRequest URL
        get_request = data.get('getRequest', '')
        target_author = self.extract_author_from_url(get_request)
        
        if not target_author:
            # Try to extract from _requestUrls if getRequest is empty
            request_urls = data.get('_requestUrls', [])
            if request_urls:
                target_author = self.extract_author_from_url(request_urls[0])
        
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
                    # Second check: Is it a match for the target author?
                    is_a_match = self.is_match(item, target_author, debug)
                    
                    record = self.parse_item(item, i)
                    
                    if debug:
                        access_info = item.get('accessInfo', {})
                        pdf_info = access_info.get('pdf', {})
                        sale_info = item.get('saleInfo', {})
                        print(f"  PDF available with downloadLink: {pdf_info.get('isAvailable', False) and 'downloadLink' in pdf_info}")
                        print(f"  Saleability FREE: {sale_info.get('saleability', '').upper() == 'FREE'}")
                        print(f"  Selected URL: {record['Url'][:100]}..." if len(record['Url']) > 100 else f"  Selected URL: {record['Url']}")
                        print(f"  Publisher: '{record['Publisher']}'")
                        print(f"  Notes (first 100 chars): '{record['Notes'][:100]}...'" if record['Notes'] else f"  Notes: '{record['Notes']}'")
                        print(f"  File Attachments: '{record['File Attachments']}'")
                    
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
                print(f"Error parsing item {i} in {json_file_path}: {e}")
                excluded_count += 1
                continue
        
        return matches_records, non_matches_records, excluded_count, target_author
    
    def parse_folder_to_csv(self, input_folder: str, matches_csv_path: str, non_matches_csv_path: str, debug: bool = False):
        """
        Parse all JSON files in a folder and create consolidated CSV outputs.
        
        Args:
            input_folder: Path to folder containing JSON files
            matches_csv_path: Path for consolidated matches CSV
            non_matches_csv_path: Path for consolidated non-matches CSV
            debug: Enable debug output
        """
        # Get all JSON files in the folder
        json_files = []
        for file in os.listdir(input_folder):
            if file.lower().endswith('.json'):
                json_files.append(os.path.join(input_folder, file))
        
        if not json_files:
            print(f"No JSON files found in {input_folder}")
            return 0, 0
        
        print(f"Found {len(json_files)} JSON files to process")
        
        # Initialize consolidated records
        all_matches = []
        all_non_matches = []
        total_excluded = 0
        total_files_processed = 0
        authors_processed = []
        
        # Process each JSON file
        for i, json_file in enumerate(json_files, 1):
            try:
                print(f"\n[{i}/{len(json_files)}] Processing: {os.path.basename(json_file)}")
                
                matches, non_matches, excluded, target_author = self.parse_json_file(json_file, debug)
                
                all_matches.extend(matches)
                all_non_matches.extend(non_matches)
                total_excluded += excluded
                total_files_processed += 1
                
                if target_author:
                    authors_processed.append(target_author)
                
                print(f"  Detected author: '{target_author}'")
                print(f"  File results: {len(matches)} matches, {len(non_matches)} non-matches, {excluded} excluded")
                
            except Exception as e:
                print(f"Error processing file {json_file}: {e}")
                continue
        
        # Write consolidated matches to CSV
        with open(matches_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.csv_headers, 
                                   quoting=csv.QUOTE_ALL, 
                                   quotechar='"')
            writer.writeheader()
            writer.writerows(all_matches)
        
        # Write consolidated non-matches to CSV
        with open(non_matches_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.csv_headers, 
                                   quoting=csv.QUOTE_ALL, 
                                   quotechar='"')
            writer.writeheader()
            writer.writerows(all_non_matches)
        
        print(f"\n{'='*60}")
        print(f"=== PROCESSING COMPLETE ===")
        print(f"{'='*60}")
        print(f"Files processed: {total_files_processed}/{len(json_files)}")
        print(f"Authors processed: {', '.join(set(authors_processed))}")
        print(f"Total matches: {len(all_matches)} items → {matches_csv_path}")
        print(f"Total non-matches: {len(all_non_matches)} items → {non_matches_csv_path}")
        print(f"Total excluded: {total_excluded} items (didn't meet inclusion criteria)")
        print(f"{'='*60}")
        
        return len(all_matches), len(all_non_matches)


# Usage example
if __name__ == "__main__":
    parser = GoogleBooksToZoteroParser()
    
    # Process an entire folder
    input_folder = "raw_gbooks_data"  # Folder containing all JSON files
    consolidated_matches_csv = "consolidated_matches.csv"
    consolidated_non_matches_csv = "consolidated_non_matches.csv"
    
    # Parse all JSON files in the folder
    match_count, non_match_count = parser.parse_folder_to_csv(
        input_folder, consolidated_matches_csv, consolidated_non_matches_csv, debug=False
    )
    print(f"\nFinal totals: {match_count} matches and {non_match_count} non-matches")