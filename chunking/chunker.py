"""
Text chunking utilities for credit agreements

Expected Articles (typically 9):
1. Definitions
2. Credits (or The Credits)
3. Representations and Warranties
4. Conditions (or Conditions to Credit Extensions)
5. Affirmative Covenants
6. Negative Covenants
7. Guarantee
8. Events of Default
9. Administrative Agent (or The Administrative Agent)
10. Miscellaneous (sometimes combined with Administrative Agent)
"""
import re
import uuid
from typing import Dict, List, Any, Optional, Tuple


def find_table_of_contents(text: str) -> Optional[Tuple[int, int]]:
    """
    Find the Table of Contents section in the text
    
    Args:
        text: Full extracted text from PDF
        
    Returns:
        Tuple of (start_index, end_index) if found, None otherwise
    """
    # Look for "Table of Contents" or "TABLE OF CONTENTS"
    toc_patterns = [
        r'Table of Contents',
        r'TABLE OF CONTENTS',
        r'Table\s+of\s+Contents',
    ]
    
    for pattern in toc_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            start_idx = match.start()
            
            # Find where TOC ends - look for patterns that indicate end
            # TOC typically ends when we see SCHEDULES or EXHIBITS sections
            remaining_text = text[start_idx:]
            end_idx = len(text)  # Default to end of text
            
            # Look for SCHEDULES or EXHIBITS (these come after TOC)
            schedules_match = re.search(r'\n\s*SCHEDULES', remaining_text, re.IGNORECASE)
            exhibits_match = re.search(r'\n\s*EXHIBITS', remaining_text, re.IGNORECASE)
            
            if schedules_match:
                end_idx = start_idx + schedules_match.start()
            elif exhibits_match:
                end_idx = start_idx + exhibits_match.start()
            
            return (start_idx, end_idx)
    
    return None


def parse_table_of_contents(text: str) -> Dict[str, Any]:
    """
    Parse the Table of Contents to extract Articles and Sections with page numbers
    
    Args:
        text: Full extracted text from PDF
        
    Returns:
        Dictionary containing:
            - articles: List of articles with their sections and page ranges
            - sections: List of all sections with their page numbers
    """
    # Find TOC section
    toc_location = find_table_of_contents(text)
    if not toc_location:
        return {
            'articles': [],
            'sections': [],
            'toc_found': False
        }
    
    start_idx, end_idx = toc_location
    toc_text = text[start_idx:end_idx]
    
    # Parse articles and sections
    articles = []
    all_sections = []
    
    # Split TOC into lines for processing
    lines = toc_text.split('\n')
    
    current_article = None
    current_article_sections = []
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            i += 1
            continue
        
        # Check if this line contains an ARTICLE
        # Pattern: "ARTICLE I", "ARTICLE I Definitions", "ARTICLE I Definitions 1"
        article_match = re.search(r'ARTICLE\s+([IVX]+(?:\d+)?)', line, re.IGNORECASE)
        if article_match:
            # Save previous article if exists
            if current_article:
                articles.append({
                    'article_number': current_article['number'],
                    'article_title': current_article['title'],
                    'start_page': current_article['start_page'],
                    'end_page': current_article.get('end_page'),
                    'sections': current_article_sections
                })
            
            # Extract article number
            article_num = article_match.group(1)
            
            # Extract article title and page number
            # Format 1: "ARTICLE I Definitions 1" - title and page on same line
            title_page_match = re.search(
                r'ARTICLE\s+[IVX]+(?:\d+)?\s+([A-Z][A-Z\s&,]+?)(?:\s+(\d+))?\s*$',
                line,
                re.IGNORECASE
            )
            
            title = ""
            start_page = None
            
            if title_page_match:
                title = title_page_match.group(1).strip()
                if title_page_match.group(2):
                    start_page = int(title_page_match.group(2))
            else:
                # Format 2: "ARTICLE I" on one line, "DEFINITIONS" on next line(s)
                # Look ahead for title
                j = i + 1
                while j < len(lines) and j < i + 3:  # Check up to 2 lines ahead
                    next_line = lines[j].strip()
                    if not next_line:
                        j += 1
                        continue
                    
                    # Check if it's a section (has section number) - stop looking
                    if re.search(r'(?:SECTION|Section)\s+\d+\.\d+', next_line, re.IGNORECASE):
                        break
                    
                    # Check if it's all caps title (not a page number line)
                    if re.match(r'^[A-Z][A-Z\s&,]+$', next_line) and not re.search(r'\d+$', next_line):
                        if title:
                            title += " " + next_line
                        else:
                            title = next_line
                        j += 1
                    else:
                        break
            
            current_article = {
                'number': article_num,
                'title': title,
                'start_page': start_page
            }
            current_article_sections = []
            i += 1
            continue
        
        # Check if this line contains a SECTION
        section_match = re.search(r'(?:SECTION|Section)\s+(\d+\.\d+[A-Z]?)(?:\.)?\s+([^\n]+?)\s+(\d+)\s*$', line, re.IGNORECASE)
        if section_match:
            section_num = section_match.group(1)
            section_title = section_match.group(2).strip()
            page_num = int(section_match.group(3))
            
            section_info = {
                'section_number': section_num,
                'section_title': section_title,
                'page_number': page_num
            }
            
            all_sections.append(section_info)
            
            if current_article:
                current_article_sections.append(section_info)
                
                # If article doesn't have start_page yet, use first section's page
                if current_article['start_page'] is None:
                    current_article['start_page'] = page_num
        
        i += 1
    
    # Save last article
    if current_article:
        articles.append({
            'article_number': current_article['number'],
            'article_title': current_article['title'],
            'start_page': current_article['start_page'],
            'end_page': current_article.get('end_page'),
            'sections': current_article_sections
        })
    
    # Determine end pages for articles
    for i in range(len(articles)):
        if i < len(articles) - 1:
            # End page is the start page of next article
            articles[i]['end_page'] = articles[i + 1]['start_page']
        else:
            # Last article - try to find end page from SCHEDULES/EXHIBITS or document end
            # Look for SCHEDULES or EXHIBITS in the full text after TOC
            remaining_text = text[end_idx:]
            schedules_match = re.search(r'\n\s*SCHEDULES', remaining_text, re.IGNORECASE)
            exhibits_match = re.search(r'\n\s*EXHIBITS', remaining_text, re.IGNORECASE)
            
            if schedules_match:
                # Try to find page number near SCHEDULES
                sched_text = remaining_text[max(0, schedules_match.start()-200):schedules_match.start()+50]
                page_match = re.search(r'---\s*Page\s+(\d+)', sched_text, re.IGNORECASE)
                if page_match:
                    articles[i]['end_page'] = int(page_match.group(1))
                else:
                    articles[i]['end_page'] = None
            elif exhibits_match:
                # Try to find page number near EXHIBITS
                exh_text = remaining_text[max(0, exhibits_match.start()-200):exhibits_match.start()+50]
                page_match = re.search(r'---\s*Page\s+(\d+)', exh_text, re.IGNORECASE)
                if page_match:
                    articles[i]['end_page'] = int(page_match.group(1))
                else:
                    articles[i]['end_page'] = None
            else:
                articles[i]['end_page'] = None
    
    return {
        'articles': articles,
        'sections': all_sections,
        'toc_found': True,
        'toc_text': toc_text,
        'article_count': len(articles)
    }


def find_article_in_text(text: str, article_num: str, article_title: str, search_start_idx: int = 0) -> Optional[int]:
    """
    Find where an article actually appears in the text by searching for article header.
    
    Args:
        text: Full extracted text
        article_num: Article number (e.g., "I", "II", "III")
        article_title: Article title from TOC (e.g., "DEFINITIONS", "THE CREDITS")
        search_start_idx: Index in text to start searching from (after TOC)
        
    Returns:
        Index in text where article starts, or None if not found
    """
    # Convert article number to different formats
    article_num_variants = [article_num]
    if article_num == 'I':
        article_num_variants.extend(['1', 'ONE'])
    elif article_num == 'II':
        article_num_variants.extend(['2', 'TWO'])
    elif article_num == 'III':
        article_num_variants.extend(['3', 'THREE'])
    elif article_num == 'IV':
        article_num_variants.extend(['4', 'FOUR'])
    elif article_num == 'V':
        article_num_variants.extend(['5', 'FIVE'])
    elif article_num == 'VI':
        article_num_variants.extend(['6', 'SIX'])
    elif article_num == 'VII':
        article_num_variants.extend(['7', 'SEVEN'])
    elif article_num == 'VIII':
        article_num_variants.extend(['8', 'EIGHT'])
    elif article_num == 'IX':
        article_num_variants.extend(['9', 'NINE'])
    elif article_num == 'X':
        article_num_variants.extend(['10', 'TEN'])
    
    # Clean article title for matching
    article_title_clean = article_title.strip().upper() if article_title else ""
    
    # Search for article patterns
    # Pattern 1: "ARTICLE X" followed by title (on same line or next line)
    for num_variant in article_num_variants:
        # Pattern: ARTICLE X followed by title
        pattern1 = rf'ARTICLE\s+{re.escape(num_variant)}\s+{re.escape(article_title_clean)}'
        pattern2 = rf'ARTICLE\s+{re.escape(num_variant)}\s*\n\s*{re.escape(article_title_clean)}'
        pattern3 = rf'ARTICLE\s+{re.escape(num_variant)}\s*\n\s*{re.escape(article_title_clean)}\s*\n'
        
        for pattern in [pattern1, pattern2, pattern3]:
            match = re.search(pattern, text[search_start_idx:], re.IGNORECASE | re.MULTILINE)
            if match:
                return search_start_idx + match.start()
    
    # Pattern 2: Just the title at start of line (for articles without "ARTICLE X" prefix)
    if article_title_clean:
        title_pattern = rf'^\s*{re.escape(article_title_clean)}\s*\n'
        match = re.search(title_pattern, text[search_start_idx:], re.IGNORECASE | re.MULTILINE)
        if match:
            return search_start_idx + match.start()
    
    return None


def get_page_for_position(text: str, pos: int) -> Optional[int]:
    """Find which PDF page a text position belongs to"""
    # Look for page markers like "--- Page X ---"
    page_pattern = r'---\s*Page\s+(\d+)\s*---'
    
    # Find all page markers and their positions
    page_markers = []
    for match in re.finditer(page_pattern, text):
        page_num = int(match.group(1))
        page_markers.append((match.start(), page_num))
    
    # Find which page the position belongs to
    for i in range(len(page_markers)):
        marker_pos, page_num = page_markers[i]
        # Check if position is after this marker
        if pos >= marker_pos:
            # Check if there's a next marker
            if i + 1 < len(page_markers):
                next_marker_pos, _ = page_markers[i + 1]
                if pos < next_marker_pos:
                    return page_num
            else:
                # Last page marker
                return page_num
    
    # If position is before first page marker, return first page or None
    if page_markers:
        return page_markers[0][1]
    return None


def classify_chunk_type(article_title: str) -> str:
    """Classify chunk type based on article title"""
    title_upper = article_title.upper() if article_title else ""
    
    if 'DEFINITION' in title_upper:
        return 'definitions'
    elif 'REPRESENTATION' in title_upper or 'WARRANT' in title_upper:
        return 'representations'
    elif 'NEGATIVE' in title_upper and 'COVENANT' in title_upper:
        return 'negative_covenants'
    elif 'COVER' in title_upper or title_upper == 'COVER PAGE':
        return 'cover'
    elif 'CONDITION' in title_upper or 'CONDITIONS' in title_upper:
        # "Conditions to Credit Extensions" should not be classified as credits
        return 'other'
    elif 'CREDIT' in title_upper:
        # Check for common credit article patterns
        # "THE CREDITS", "CREDITS", "CREDIT FACILITIES", etc.
        if any(pattern in title_upper for pattern in ['THE CREDITS', 'CREDITS', 'CREDIT FACILITIES', 'CREDIT FACILITY']):
            return 'credits'
        # If it just has "CREDIT" but doesn't match specific patterns, be conservative
        return 'other'
    elif 'EVENT' in title_upper and 'DEFAULT' in title_upper:
        return 'events_of_default'
    else:
        return 'other'


class DocumentChunker:
    """Chunk credit agreement documents into semantic articles using TOC parsing"""
    
    def chunk(self, text: str) -> List[Dict]:
        """
        Chunk document into articles using Table of Contents
        
        Returns list of chunks with:
        {
            'chunkId': str,
            'chunkType': str,
            'title': str,
            'text': str,
            'metadata': {
                'charCount': int,
                'startPage': int,
                'endPage': int
            }
        }
        """
        chunks = []
        
        # Parse TOC to get list of articles
        toc_data = parse_table_of_contents(text)
        
        if not toc_data['toc_found'] or not toc_data['articles']:
            # Fallback: try simple pattern matching
            return self._fallback_chunk(text)
        
        articles = toc_data['articles']
        
        # Find where TOC ends
        toc_location = find_table_of_contents(text)
        toc_end_idx = toc_location[1] if toc_location else 0
        
        # Find where each article actually starts in the text
        article_positions = []
        search_start = toc_end_idx
        
        for article in articles:
            article_num = article['article_number']
            article_title = article['article_title'] or ""
            
            # Find this article in the text
            article_start_idx = find_article_in_text(text, article_num, article_title, search_start)
            
            if article_start_idx:
                article_positions.append({
                    'article': article,
                    'text_start_idx': article_start_idx,
                    'article_num': article_num,
                    'article_title': article_title
                })
                # Next search starts after this article
                search_start = article_start_idx + 100  # Small offset to avoid matching same article
        
        if not article_positions:
            # Fallback if we can't find articles
            return self._fallback_chunk(text)
        
        # Create chunks
        # Chunk 1: Cover page to before first article
        first_article_pos = article_positions[0]['text_start_idx']
        cover_text = text[:first_article_pos].strip()
        
        if cover_text and len(cover_text) > 100:
            cover_start_page = get_page_for_position(text, 0)
            cover_end_page = get_page_for_position(text, first_article_pos - 1)
            
            chunks.append({
                'chunkId': str(uuid.uuid4()),
                'chunkType': 'cover',
                'title': 'Cover Page',
                'text': cover_text,
                'metadata': {
                    'charCount': len(cover_text),
                    'startPage': cover_start_page or 1,
                    'endPage': cover_end_page or (get_page_for_position(text, first_article_pos) or 1)
                }
            })
        
        # Chunks 2-N: Each article
        for i, art_pos in enumerate(article_positions):
            article = art_pos['article']
            article_start_idx = art_pos['text_start_idx']
            
            # Find end of this article (start of next article, or end of text)
            if i + 1 < len(article_positions):
                article_end_idx = article_positions[i + 1]['text_start_idx']
            else:
                article_end_idx = len(text)
            
            # Extract text for this article
            article_text = text[article_start_idx:article_end_idx].strip()
            
            # Get page numbers
            start_page_pdf = get_page_for_position(text, article_start_idx) or article.get('start_page')
            end_page_pdf = get_page_for_position(text, article_end_idx - 1) or article.get('end_page')
            
            # Classify chunk type
            chunk_type = classify_chunk_type(article['article_title'])
            
            # Skip if classified as 'other' (unless it's a known type we want)
            if chunk_type == 'other':
                # Still include it but mark as other
                pass
            
            chunk_name = article['article_title'] if article['article_title'] else f"Article {article['article_number']}"
            
            chunks.append({
                'chunkId': str(uuid.uuid4()),
                'chunkType': chunk_type,
                'title': chunk_name,
                'text': article_text,
                'metadata': {
                    'charCount': len(article_text),
                    'startPage': start_page_pdf or 1,
                    'endPage': end_page_pdf or 1
                }
            })
        
        return chunks
    
    def _fallback_chunk(self, text: str) -> List[Dict]:
        """Fallback chunking using simple pattern matching"""
        chunks = []
        
        # Simple article patterns
        article_patterns = [
            (r'ARTICLE\s+[IVX]+[\.\s]*[-–—]?\s*DEFINITIONS', 'definitions'),
            (r'ARTICLE\s+[IVX]+[\.\s]*[-–—]?\s*REPRESENTATIONS', 'representations'),
            (r'ARTICLE\s+[IVX]+[\.\s]*[-–—]?\s*NEGATIVE\s+COVENANTS', 'negative_covenants'),
            (r'ARTICLE\s+[IVX]+[\.\s]*[-–—]?\s*CREDITS?', 'credits'),
            (r'ARTICLE\s+[IVX]+[\.\s]*[-–—]?\s*EVENTS?\s+OF\s+DEFAULT', 'events_of_default'),
        ]
        
        article_starts = []
        for pattern, chunk_type in article_patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE))
            for match in matches:
                article_starts.append({
                    'position': match.start(),
                    'type': chunk_type,
                    'title': match.group(0).strip()
                })
        
        article_starts.sort(key=lambda x: x['position'])
        
        # Extract chunks
        for i, article_start in enumerate(article_starts):
            start_pos = article_start['position']
            end_pos = article_starts[i + 1]['position'] if i + 1 < len(article_starts) else len(text)
            
            chunk_text = text[start_pos:end_pos].strip()
            
            chunks.append({
                'chunkId': str(uuid.uuid4()),
                'chunkType': article_start['type'],
                'title': article_start['title'],
                'text': chunk_text,
                'metadata': {
                    'charCount': len(chunk_text),
                    'startPage': get_page_for_position(text, start_pos) or 1,
                    'endPage': get_page_for_position(text, end_pos - 1) or 1
                }
            })
        
        return chunks
