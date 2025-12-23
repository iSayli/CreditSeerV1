import pdfplumber
import PyPDF2
from typing import Dict, List

class PDFProcessor:
    """Process PDF files to extract text with table detection"""
    
    def __init__(self):
        self.table_count = 0
    
    def process(self, filepath: str) -> Dict:
        """
        Process PDF and extract text
        
        Returns:
            {
                'text': str,
                'metadata': {
                    'pageCount': int,
                    'charCount': int,
                    'tableCount': int
                }
            }
        """
        text_parts = []
        page_count = 0
        self.table_count = 0
        
        # Use pdfplumber for better text extraction and table detection
        with pdfplumber.open(filepath) as pdf:
            page_count = len(pdf.pages)
            
            for page_num, page in enumerate(pdf.pages, 1):
                # Add page marker
                text_parts.append(f"--- Page {page_num} ---")
                
                # Extract main text
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
                
                # Detect tables
                try:
                    tables = page.extract_tables()
                    if tables:
                        self.table_count += len(tables)
                        # Convert tables to text representation
                        for table in tables:
                            try:
                                table_text = self._table_to_text(table)
                                if table_text:
                                    text_parts.append(table_text)
                            except Exception:
                                # Skip tables that can't be converted
                                continue
                except Exception:
                    # Continue processing even if table extraction fails
                    pass
        
        # Fallback to PyPDF2 if pdfplumber fails
        if not text_parts:
            with open(filepath, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                page_count = len(pdf_reader.pages)
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    # Add page marker
                    text_parts.append(f"--- Page {page_num} ---")
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
        
        full_text = '\n\n'.join(text_parts)
        
        return {
            'text': full_text,
            'metadata': {
                'pageCount': page_count,
                'charCount': len(full_text),
                'tableCount': self.table_count
            }
        }
    
    def _table_to_text(self, table: List[List]) -> str:
        """Convert table structure to normalized text"""
        if not table:
            return ""
        
        rows = []
        for row in table:
            if row:
                # Filter out None values and join with tabs
                clean_row = [str(cell) if cell else "" for cell in row]
                rows.append("\t".join(clean_row))
        
        return "\n".join(rows)

