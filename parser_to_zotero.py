import csv
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os

class ZoteroCSVtoRDFConverter:
    """Convert Zotero CSV export to RDF format using dc:subject for attachments"""
    
    # Namespace definitions
    NAMESPACES = {
        'rdf': "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        'z': "http://www.zotero.org/namespaces/export#",
        'bib': "http://purl.org/net/biblio#",
        'foaf': "http://xmlns.com/foaf/0.1/",
        'dcterms': "http://purl.org/dc/terms/",
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
        'memo': 'bib:Memo'
    }
    
    def __init__(self):
        self.root = None
        self.item_counter = 1
        self.note_counter = 1
        
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
    
    def create_subject_element(self, attachment_string):
        """Create subject element for file attachments using dcterms:LCC"""
        if not attachment_string:
            return None
            
        subject_elem = ET.Element('dc:subject')
        lcc_elem = ET.SubElement(subject_elem, 'dcterms:LCC')
        value_elem = ET.SubElement(lcc_elem, 'rdf:value')
        
        # Use the attachment string as-is
        value_elem.text = attachment_string
        
        return subject_elem
    
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
        
        # Add file attachments to subject field
        file_attachments = row.get('File Attachments', '')
        if file_attachments:
            # Take the first attachment if multiple are separated by semicolon
            first_attachment = file_attachments.split(';')[0].strip()
            if first_attachment:
                subject_elem = self.create_subject_element(first_attachment)
                if subject_elem is not None:
                    item_elem.append(subject_elem)
        
        # If no file attachments, check for link attachments
        elif row.get('Link Attachments', ''):
            link_attachments = row.get('Link Attachments', '')
            first_attachment = link_attachments.split(';')[0].strip()
            if first_attachment:
                subject_elem = self.create_subject_element(first_attachment)
                if subject_elem is not None:
                    item_elem.append(subject_elem)
        
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
        
        # Add publication title/source
        pub_title = row.get('Publication Title', '')
        if pub_title:
            source_elem = ET.SubElement(item_elem, 'dc:source')
            source_elem.text = pub_title
        
        # Add publisher
        publisher = row.get('Publisher', '')
        if publisher:
            pub_elem = ET.SubElement(item_elem, 'dc:publisher')
            pub_elem.text = publisher
        
        # Add place/location
        place = row.get('Place', '')
        if place:
            place_elem = ET.SubElement(item_elem, 'dc:location')
            place_elem.text = place
        
        # Add rights
        rights = row.get('Rights', '')
        if rights:
            rights_elem = ET.SubElement(item_elem, 'dc:rights')
            rights_elem.text = rights
        
        # Add type
        doc_type = row.get('Type', '')
        if doc_type:
            type_elem = ET.SubElement(item_elem, 'dc:type')
            type_elem.text = doc_type
    
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


# Test function with your example CSV structure
def test_conversion():
    """Test the converter with your example data"""
    converter = ZoteroCSVtoRDFConverter()
    
    # Create a test CSV with your data structure
    csv_content = '''"Key","Item Type","Publication Year","Author","Title","Publication Title","ISBN","ISSN","DOI","Url","Abstract Note","Date","Date Added","Date Modified","Access Date","Pages","Num Pages","Issue","Volume","Number Of Volumes","Journal Abbreviation","Short Title","Series","Series Number","Series Text","Series Title","Publisher","Place","Language","Rights","Type","Archive","Archive Location","Library Catalog","Call Number","Extra","Notes","File Attachments","Link Attachments","Manual Tags","Automatic Tags","Editor","Series Editor","Translator","Contributor","Attorney Agent","Book Author","Cast Member","Commenter","Composer","Cosponsor","Counsel","Interviewer","Producer","Recipient","Reviewed Author","Scriptwriter","Words By","Guest","Number","Edition","Running Time","Scale","Medium","Artwork Size","Filing Date","Application Number","Assignee","Issuing Authority","Country","Meeting Name","Conference Name","Court","References","Reporter","Legal Status","Priority Numbers","Programming Language","Version","System","Code","Code Number","Section","Session","Committee","History","Legislative Body"
"","book","1885","Fabrega, Henri François Pittier De","The Flora of the Pays D'Enhaut (Switzerland): A Botanical Account","","","","","https://books.google.com/books/download/the_flora_of_the_pays_denhaut_switzerland.pdf?id=lr7DbrTgJk0C&output=pdf","","1885","2025-12-12 21:29:21","2025-12-12 21:29:21","","","22","","","","","","","","","","","","en","","","Google Books","","","","Venezuela","Analyse: Description sommaire.","http://books.google.com/books/content?id=lr7DbrTgJk0C&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","",""'''
    
    # Write test CSV file
    with open('test_zotero.csv', 'w', encoding='utf-8') as f:
        f.write(csv_content)
    
    # Convert to RDF
    converter.convert_csv_to_rdf('test_zotero.csv', 'output.rdf')
    
    # Display the result
    print("Generated RDF output:")
    print("-" * 80)
    with open('output.rdf', 'r', encoding='utf-8') as f:
        print(f.read())


# Example of how to use the converter
def main():
    """Main function to run the converter"""
    converter = ZoteroCSVtoRDFConverter()
    
    # Convert your actual CSV file
    input_csv = "zotero.csv"  # Change to your CSV file name
    output_rdf = "zotero_output.rdf"  # Output RDF file name
    
    try:
        converter.convert_csv_to_rdf(input_csv, output_rdf)
        print(f"\nConversion complete! Check '{output_rdf}' for the RDF output.")
    except FileNotFoundError:
        print(f"Error: File '{input_csv}' not found.")
        print("Creating a sample file and trying again...")
        test_conversion()


if __name__ == "__main__":
    main()