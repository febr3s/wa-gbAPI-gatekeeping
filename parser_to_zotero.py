import csv
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os

class ZoteroCSVtoRDFConverter:
    """Convert Zotero CSV export to RDF format"""
    
    # Namespace definitions
    NAMESPACES = {
        'rdf': "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        'z': "http://www.zotero.org/namespaces/export#",
        'bib': "http://purl.org/net/biblio#",
        'foaf': "http://xmlns.com/foaf/0.1/",
        'dcterms': "http://purl.org/dc/terms/",
        'link': "http://purl.org/rss/1.0/modules/link/",
        'dc': "http://purl.org/dc/elements/1.1/"
    }
    
    # Item type mappings from CSV to RDF
    ITEM_TYPE_MAPPING = {
        'book': 'bib:Book',
        'journalArticle': 'bib:Article',
        'bookSection': 'bib:Chapter',
        'thesis': 'bib:Thesis',
        'conferencePaper': 'bib:Paper',
        'report': 'bib:Report',
        'document': 'bib:Document',
        'memo': 'bib:Memo',
        'attachment': 'z:Attachment'
    }
    
    def __init__(self):
        self.root = None
        self.item_counter = 1
        self.note_counter = 1
        self.attachment_counter = 1
        
    def register_namespaces(self):
        """Register all namespaces for proper XML output"""
        for prefix, uri in self.NAMESPACES.items():
            ET.register_namespace(prefix, uri)
    
    def create_rdf_root(self):
        """Create the RDF root element with namespaces"""
        root = ET.Element('rdf:RDF')
        for prefix, uri in self.NAMESPACES.items():
            root.set(f'xmlns:{prefix}', uri)
        return root
    
    def parse_author_string(self, author_string):
        """Parse author string from CSV into structured format"""
        if not author_string:
            return []
        
        authors = []
        # Split multiple authors (usually separated by semicolon in Zotero)
        author_list = author_string.split(';')
        
        for author in author_list:
            author = author.strip()
            if not author:
                continue
                
            # Try to parse "Lastname, Firstname" format
            if ',' in author:
                parts = author.split(',', 1)
                surname = parts[0].strip()
                given_name = parts[1].strip() if len(parts) > 1 else ''
            else:
                # Try to parse "Firstname Lastname" format
                parts = author.rsplit(' ', 1)
                if len(parts) == 2:
                    given_name = parts[0].strip()
                    surname = parts[1].strip()
                else:
                    surname = author
                    given_name = ''
            
            authors.append({
                'surname': surname,
                'givenName': given_name
            })
        
        return authors
    
    def create_author_element(self, authors):
        """Create RDF author element"""
        if not authors:
            return None
            
        authors_elem = ET.Element('bib:authors')
        seq_elem = ET.SubElement(authors_elem, 'rdf:Seq')
        
        for author in authors:
            li_elem = ET.SubElement(seq_elem, 'rdf:li')
            person_elem = ET.SubElement(li_elem, 'foaf:Person')
            
            if author.get('surname'):
                surname_elem = ET.SubElement(person_elem, 'foaf:surname')
                surname_elem.text = author['surname']
            
            if author.get('givenName'):
                given_name_elem = ET.SubElement(person_elem, 'foaf:givenName')
                given_name_elem.text = author['givenName']
        
        return authors_elem
    
    def create_identifier_element(self, value):
        """Create identifier element for URLs"""
        if not value:
            return None
            
        identifier_elem = ET.Element('dc:identifier')
        
        # For URLs, create URI element
        if value.startswith('http://') or value.startswith('https://'):
            uri_elem = ET.SubElement(identifier_elem, 'dcterms:URI')
            value_elem = ET.SubElement(uri_elem, 'rdf:value')
            value_elem.text = value
        else:
            # For other identifiers
            identifier_elem.text = value
        
        return identifier_elem
    
    def create_item_element(self, row, item_key):
        """Create main item element based on item type"""
        item_type = row.get('Item Type', 'book').lower()
        rdf_type = self.ITEM_TYPE_MAPPING.get(item_type, 'bib:Book')
        
        # Create about attribute - use URL if available, otherwise generate ID
        about_url = row.get('Url', '')
        if about_url and ('http://' in about_url or 'https://' in about_url):
            about_attr = about_url
        else:
            about_attr = f"#item_{item_key}"
        
        return ET.Element(rdf_type, attrib={'rdf:about': about_attr})
    
    def add_basic_fields(self, item_elem, row):
        """Add basic fields to the item element"""
        # Add itemType
        item_type_elem = ET.SubElement(item_elem, 'z:itemType')
        item_type_elem.text = row.get('Item Type', 'book').lower()
        
        # Add authors
        author_string = row.get('Author', '')
        if author_string:
            authors = self.parse_author_string(author_string)
            author_elem = self.create_author_element(authors)
            if author_elem is not None:
                item_elem.append(author_elem)
        
        # Add title
        title = row.get('Title', '')
        if title:
            title_elem = ET.SubElement(item_elem, 'dc:title')
            title_elem.text = title
        
        # Add date (prioritize Publication Year, then Date)
        date_value = row.get('Publication Year', '') or row.get('Date', '')
        if date_value:
            date_elem = ET.SubElement(item_elem, 'dc:date')
            date_elem.text = date_value
        
        # Add language
        language = row.get('Language', '')
        if language:
            language_elem = ET.SubElement(item_elem, 'z:language')
            language_elem.text = language
        
        # Add archive
        archive = row.get('Archive', '')
        if archive:
            archive_elem = ET.SubElement(item_elem, 'z:archive')
            archive_elem.text = archive
        
        # Add identifier (URL)
        url = row.get('Url', '')
        if url:
            identifier_elem = self.create_identifier_element(url)
            if identifier_elem is not None:
                item_elem.append(identifier_elem)
        
        # Add description/abstract
        description = row.get('Abstract Note', '')
        if description:
            desc_elem = ET.SubElement(item_elem, 'dc:description')
            desc_elem.text = description
        
        # Add extra field if present
        extra = row.get('Extra', '')
        if extra:
            extra_elem = ET.SubElement(item_elem, 'dc:description')
            if description:
                extra_elem.text = f"{description} {extra}"
            else:
                extra_elem.text = extra
        
        # Add number of pages
        num_pages = row.get('Num Pages', '')
        if num_pages:
            pages_elem = ET.SubElement(item_elem, 'z:numPages')
            pages_elem.text = num_pages
    
    def create_note_element(self, note_content, note_id):
        """Create note element for referenced notes"""
        if not note_content:
            return None
        
        note_elem = ET.Element('bib:Memo', attrib={'rdf:about': f"#item_{note_id}"})
        value_elem = ET.SubElement(note_elem, 'rdf:value')
        
        # Format note content similar to Zotero's format
        formatted_note = f'<div data-schema-version="8"><p>{note_content}</p></div>'
        value_elem.text = formatted_note
        
        return note_elem
    
    def extract_attachment_info(self, attachment_string):
        """Extract filename and path from attachment string"""
        if not attachment_string:
            return None, None
        
        # Zotero CSV attachment format can vary
        # Common formats: "filename.pdf" or "path/to/file:filename.pdf"
        
        # Split by colon (common in Zotero exports)
        if ':' in attachment_string:
            # Format like "path:filename.pdf"
            parts = attachment_string.split(':')
            filename = parts[-1].strip() if parts[-1] else "attachment"
        else:
            # Just a filename or path
            filename = os.path.basename(attachment_string)
        
        # Clean up the filename
        filename = filename.strip()
        
        # Get MIME type from extension
        mime_type = self.get_mime_type(filename)
        
        return filename, mime_type
    
    def get_mime_type(self, filename):
        """Determine MIME type from filename extension"""
        filename_lower = filename.lower()
        
        if filename_lower.endswith('.pdf'):
            return 'application/pdf'
        elif filename_lower.endswith('.txt'):
            return 'text/plain'
        elif filename_lower.endswith(('.jpg', '.jpeg')):
            return 'image/jpeg'
        elif filename_lower.endswith('.png'):
            return 'image/png'
        elif filename_lower.endswith('.gif'):
            return 'image/gif'
        elif filename_lower.endswith(('.doc', '.docx')):
            return 'application/msword'
        elif filename_lower.endswith(('.xls', '.xlsx')):
            return 'application/vnd.ms-excel'
        elif filename_lower.endswith(('.ppt', '.pptx')):
            return 'application/vnd.ms-powerpoint'
        elif filename_lower.endswith('.html'):
            return 'text/html'
        else:
            return 'text/plain'  # default
    
    def create_attachment_element(self, attachment_string, attachment_id):
        """Create attachment element from attachment string"""
        if not attachment_string:
            return None
        
        filename, mime_type = self.extract_attachment_info(attachment_string)
        if not filename:
            return None
        
        attach_elem = ET.Element('z:Attachment', attrib={'rdf:about': f"#item_{attachment_id}"})
        
        # Add item type
        type_elem = ET.SubElement(attach_elem, 'z:itemType')
        type_elem.text = 'attachment'
        
        # Add title (filename)
        title_elem = ET.SubElement(attach_elem, 'dc:title')
        title_elem.text = filename
        
        # Add link type (MIME type)
        link_elem = ET.SubElement(attach_elem, 'link:type')
        link_elem.text = mime_type
        
        return attach_elem
    
    def convert_csv_to_rdf(self, csv_file_path, output_rdf_path):
        """Main conversion method"""
        self.register_namespaces()
        self.root = self.create_rdf_root()
        
        # Read CSV file
        with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
            # Try to detect delimiter
            sample = csvfile.read(1024)
            csvfile.seek(0)
            
            delimiter = ',' if ',' in sample else '\t'
            
            # Read CSV with proper handling of quoted fields
            reader = csv.DictReader(csvfile, delimiter=delimiter, quotechar='"')
            
            for row in reader:
                # Clean up row data (strip whitespace from values)
                cleaned_row = {k: v.strip() if isinstance(v, str) else v for k, v in row.items()}
                
                # Generate item key
                item_key = self.item_counter
                
                # Create main item element
                item_elem = self.create_item_element(cleaned_row, item_key)
                
                # Add basic fields
                self.add_basic_fields(item_elem, cleaned_row)
                
                # Handle notes (if present)
                notes = cleaned_row.get('Notes', '')
                if notes:
                    note_id = f"{item_key}_{self.note_counter}"
                    note_elem = self.create_note_element(notes, note_id)
                    if note_elem is not None:
                        self.root.append(note_elem)
                    
                    # Add reference from main item to note
                    ref_elem = ET.SubElement(item_elem, 'dcterms:isReferencedBy')
                    ref_elem.set('rdf:resource', f"#item_{note_id}")
                    self.note_counter += 1
                
                # Handle file attachments (if present)
                file_attachments = cleaned_row.get('File Attachments', '')
                if file_attachments:
                    # Zotero CSV typically has attachments separated by semicolon
                    attachments = [a.strip() for a in file_attachments.split(';') if a.strip()]
                    
                    for attachment_string in attachments:
                        if attachment_string:  # Check not empty
                            attach_id = f"{item_key}_{self.attachment_counter}"
                            attach_elem = self.create_attachment_element(attachment_string, attach_id)
                            if attach_elem is not None:
                                self.root.append(attach_elem)
                            
                            # Add link from main item to attachment
                            link_elem = ET.SubElement(item_elem, 'link:link')
                            link_elem.set('rdf:resource', f"#item_{attach_id}")
                            self.attachment_counter += 1
                
                # Also check Link Attachments column
                link_attachments = cleaned_row.get('Link Attachments', '')
                if link_attachments and not file_attachments:  # Only if no file attachments
                    attachments = [a.strip() for a in link_attachments.split(';') if a.strip()]
                    
                    for attachment_string in attachments:
                        if attachment_string:
                            attach_id = f"{item_key}_{self.attachment_counter}"
                            attach_elem = self.create_attachment_element(attachment_string, attach_id)
                            if attach_elem is not None:
                                self.root.append(attach_elem)
                            
                            # Add link from main item to attachment
                            link_elem = ET.SubElement(item_elem, 'link:link')
                            link_elem.set('rdf:resource', f"#item_{attach_id}")
                            self.attachment_counter += 1
                
                # Add item to root
                self.root.append(item_elem)
                self.item_counter += 1
        
        # Convert to pretty XML
        xml_string = ET.tostring(self.root, encoding='unicode')
        
        # Parse with minidom for pretty printing
        dom = minidom.parseString(xml_string)
        pretty_xml = dom.toprettyxml(indent='    ')
        
        # Remove extra blank lines
        pretty_xml = '\n'.join([line for line in pretty_xml.split('\n') if line.strip()])
        
        # Write to file
        with open(output_rdf_path, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)
        
        print(f"Successfully converted CSV to RDF. Output saved to: {output_rdf_path}")
        return True


# Example usage
def convert_zotero_csv_to_rdf():
    """Convert Zotero CSV to RDF format"""
    converter = ZoteroCSVtoRDFConverter()
    
    # Example with the provided CSV structure
    csv_content = """Key,Item Type,Title,Author,Publication Year,File Attachments
,book,Gramatica de la lengua castellana,Bello, Andrés,1875,this is an attachment.txt
,book,The Flora of the Pays D'Enhaut,Fabrega, Henri François Pittier De,1885,flora.pdf;notes.txt"""
    
    # Write sample CSV
    with open('zotero_sample.csv', 'w', encoding='utf-8') as f:
        f.write(csv_content)
    
    # Convert to RDF
    converter.convert_csv_to_rdf('zotero_sample.csv', 'zotero_output.rdf')
    
    # Read and display the result
    with open('zotero_output.rdf', 'r', encoding='utf-8') as f:
        print(f.read())


if __name__ == "__main__":
    convert_zotero_csv_to_rdf()