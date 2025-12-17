import os
import re
from openai import OpenAI
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv()

class Stage2Extractor:
    """Stage 2: Extract structured values from Stage 1 blocks"""
    
    def __init__(self):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    
    def extract(self, block: Dict, chunk_type: str, schema: Dict) -> Dict:
        """
        Extract values from a Stage 1 block
        
        Returns:
        {
            'blockId': str,
            'valueType': str,
            'values': Dict,
            'confidence': Dict
        }
        """
        block_id = block.get('blockId')
        value_type = block.get('valueType')
        block_text = block.get('text', '')
        
        if not block_text or block_text == 'Not Found':
            return {
                'blockId': block_id,
                'valueType': value_type,
                'values': {},
                'confidence': {}
            }
        
        # Get schema section for this valueType
        value_type_schema = self._get_value_type_schema(schema, value_type)
        if not value_type_schema:
            return {
                'blockId': block_id,
                'valueType': value_type,
                'values': {},
                'confidence': {}
            }
        
        # Build prompt
        prompt = self._build_prompt(block_id, block_text, value_type, value_type_schema, schema)
        
        # Call LLM
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert legal document analyst specializing in credit agreements."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        # Parse response
        output_text = response.choices[0].message.content
        values = self._parse_output(output_text, value_type_schema)
        confidence = self._calculate_confidence(values, block_text, value_type_schema)
        
        return {
            'blockId': block_id,
            'valueType': value_type,
            'values': values,
            'confidence': confidence
        }
    
    def _get_value_type_schema(self, schema: Dict, value_type: str) -> Dict:
        """Get schema section for specific valueType"""
        if 'schemasByValueType' in schema:
            return schema['schemasByValueType'].get(value_type, {})
        return {}
    
    def _build_prompt(self, block_id: str, block_text: str, value_type: str, value_type_schema: Dict, full_schema: Dict) -> str:
        """Build Stage 2 extraction prompt"""
        schema_str = self._format_schema_for_prompt(value_type_schema)
        
        prompt = f"""You are an expert legal document analyst specializing in credit agreements.

Your task is to EXTRACT STRUCTURED VALUES from previously isolated legal text blocks.

This is STAGE 2 of a two-stage extraction system.

────────────────────────────────────────
CRITICAL RULES (STAGE 2)
────────────────────────────────────────
1. Extract values ONLY from the provided block text.
2. Never use text outside the block.
3. Never infer missing values.
4. Use schema extraction hints as guidance, not strict regex rules.
5. Do NOT mix values across blocks.
6. For each field, the output MUST be either:
   • verbatim text copied from the block text if it exists (default behavior), 
   • a CONCISE SUMMARY if outputMode = "summarized" is defined in the schema (see below for summary rules), or
   • the exact string "Not Found" if it does not exist. 
7. You must display the field name even if the value is "Not Found".
────────────────────────────────────────
BLOCK ROUTING RULE
────────────────────────────────────────
Each block has an associated ValueType.

You MUST:
• Match the block's ValueType to the corresponding schema section.
• Extract ONLY the fields defined for that ValueType.
• Ignore schema sections that do not match the block's ValueType.

────────────────────────────────────────
OUTPUT REQUIREMENTS
────────────────────────────────────────
For EACH block, output values in this format:

BlockId: <blockId>
FieldName: Extracted Value
FieldName: Extracted Value

• One line per extracted field.
• For fields marked CollectMultiple=true, output ONE LINE PER VALUE. Repeat the FieldName for each extracted value.
• Use exact schema field names.
• Do NOT output JSON.
• Do NOT include explanations.
• If outputMode = "summarized" is specified in the schema:
  - You MUST produce a CONCISE SUMMARY, NOT verbatim text.
  - The summary should capture the essential meaning and structure.
  - Use ONLY information explicitly present in the block text.
  - Do NOT add interpretations, simplifications, or external knowledge.
  - Preserve all material calculation mechanics, fallbacks, and key components.
  - Use plain, analyst-readable language.
  - Example: Instead of copying the entire definition verbatim, summarize it as "the greatest of (a) Prime Rate plus 1.00%, (b) LIBOR plus 1.50%, and (c) SOFR plus 2.00%"

────────────────────────────────────────
ILLUSTRATIVE EXAMPLES (DO NOT EXTRACT FROM THESE)
────────────────────────────────────────

Example 1: Regular field (verbatim extraction)
Block (ValueType: covenant):
SECTION XYZ. Example Covenant
Commencing with the fiscal quarter ending Example Date, the Borrower shall not
permit the Example Covenant, in each case on the last day of any Test Period,
to be greater than the Example Threshold set forth below opposite such last day:
Last day of Test Period     Example Threshold
Example Date 1                Example Threshold Value 1
Example Date 2                Example Threshold Value 2

Output:
operator: shall not permit to be greater than
thresholdValues: Example Threshold Value 1
thresholdValues: Example Threshold Value 2
dates: Example Date 1
dates: Example Date 2

Example 2: Summarized field (outputMode = "summarized")
Block (ValueType: rate):
BlockText: "Alternate Base Rate" means, for any day, a rate per annum equal to the greatest of (a) the Prime Rate in effect on such day, (b) the Federal Funds Effective Rate in effect on such day plus 1/2 of 1%, and (c) the Adjusted LIBO Rate for a one month Interest Period on such day (or if such day is not a Business Day, the immediately preceding Business Day) plus 1%, provided that, for the avoidance of doubt, the Adjusted LIBO Rate for any day shall be based on the rate appearing on Reuters Screen LIBOR01 Page (or on any successor or substitute page of such service, or any successor to or substitute for such service, providing rate quotations comparable to those currently provided on such page of such service, as determined by the Administrative Agent from time to time for purposes of providing quotations of interest rates applicable to dollar deposits in the London interbank market) at approximately 11:00 a.m., London time, on such day.

Output (SUMMARIZED, not verbatim):
rateDefinition: the greatest of (a) Prime Rate, (b) Federal Funds Effective Rate plus 0.50%, and (c) Adjusted LIBO Rate for one month plus 1.00%

Note: The summarized version captures the essential structure and components without copying the entire verbose definition.

────────────────────────────────────────
TABLE EXTRACTION RULE
────────────────────────────────────────
If the block contains a table or schedule:
• Treat column headers as labels, not values.
• Each row represents a separate pair.
• Extract values row-by-row.
• Ignore column header text.
• Preserve row order as it appears.

────────────────────────────────────────
STAGE 2 SCHEMA
────────────────────────────────────────
{schema_str}

────────────────────────────────────────
INPUT BLOCKS
────────────────────────────────────────
BlockId: {block_id}
ValueType: {value_type}
BlockText: {block_text}

────────────────────────────────────────
BEGIN STAGE 2 EXTRACTION
────────────────────────────────────────"""
        
        return prompt
    
    def _format_schema_for_prompt(self, value_type_schema: Dict) -> str:
        """Format schema for prompt"""
        if not value_type_schema:
            return "No schema defined for this valueType"
        
        schema_lines = []
        for field_name, field_def in value_type_schema.items():
            schema_lines.append(f"FieldName: {field_name}")
            hint = field_def.get('extractionHint', {})
            pattern = hint.get('pattern', '')
            notes = hint.get('notes', '')
            field_type = hint.get('type', '')
            collect_multiple = field_def.get('collectMultiple', False)
            output_mode = field_def.get('outputMode', '')
            
            schema_lines.append(f"  Pattern: {pattern}")
            schema_lines.append(f"  Type: {field_type}")
            if output_mode == 'summarized':
                # Override notes to emphasize summarization requirement
                schema_lines.append(f"  Notes: {notes}")
                schema_lines.append(f"  OutputMode: summarized")
                schema_lines.append(f"  ⚠️ CRITICAL: This field REQUIRES a CONCISE SUMMARY, NOT verbatim text. Summarize the key components and structure while preserving all material calculation mechanics.")
            else:
                schema_lines.append(f"  Notes: {notes}")
            if collect_multiple:
                schema_lines.append(f"  CollectMultiple: true")
            schema_lines.append("")
        
        return "\n".join(schema_lines)
    
    def _parse_output(self, output_text: str, schema: Dict) -> Dict:
        """Parse LLM output into structured values"""
        values = {}
        
        lines = output_text.split('\n')
        current_field = None
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('BlockId:'):
                continue
            
            # Check if this is a field name
            if ':' in line:
                parts = line.split(':', 1)
                field_name = parts[0].strip()
                field_value = parts[1].strip() if len(parts) > 1 else ""
                
                # Check if this field exists in schema
                if field_name in schema:
                    current_field = field_name
                    collect_multiple = schema[field_name].get('collectMultiple', False)
                    
                    if collect_multiple:
                        if field_name not in values:
                            values[field_name] = []
                        if field_value and field_value != 'Not Found':
                            values[field_name].append(field_value)
                    else:
                        values[field_name] = field_value if field_value else "Not Found"
                else:
                    # Still capture if it looks like a field
                    if not current_field:
                        values[field_name] = field_value if field_value else "Not Found"
        
        return values
    
    def _calculate_confidence(self, values: Dict, block_text: str, schema_for_value_type: Dict) -> Dict:
        """
        Calculate confidence levels for extracted values with type-aware validation
        
        Uses improved multi-factor model:
        1. Presence (0-3): Value found or not
        2. Format Validity (0-2): Type-aware regex validation
        3. Evidence Support (0-2): Exact match for numbers; token coverage for text
        4. Completeness (0-1): List count sanity / table rows found
        5. Anchor Proximity (0-1): Distance to schema pattern anchor
        6. Ambiguity Penalty (-0.5 to 0): Multiple candidates in block
        7. Faithfulness (0-1): For summarized outputs, check against source
        
        Displays percentage capped at 95% to avoid false certainty.
        """
        confidence = {}
        
        # Stopwords to ignore in evidence locality checks
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                     'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be', 
                     'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 
                     'would', 'should', 'could', 'may', 'might', 'must', 'can', 'shall'}
        
        for field_name, value in values.items():
            factors = []
            score = 0
            max_score = 0
            is_missing = False
            
            # Get field type and schema info
            field_type = None
            is_summarized = False
            pattern_hint = None
            field_def = {}
            
            if field_name in schema_for_value_type:
                field_def = schema_for_value_type[field_name]
                extraction_hint = field_def.get('extractionHint', {})
                field_type = extraction_hint.get('type', 'text')
                is_summarized = field_def.get('outputMode') == 'summarized'
                pattern_hint = extraction_hint.get('pattern')
            
            # Initialize ambiguity flags
            ambiguous_candidates = False
            multiple_matches = 0
            anchor_not_found = False
            
            # Initialize value_str for use in later factors
            value_str = ''
            if not (value == "Not Found" or (isinstance(value, list) and len(value) == 0)):
                if isinstance(value, list):
                    value_str = ' '.join(str(v) for v in value)
                else:
                    value_str = str(value)
            
            # Factor 1: Value Presence (0-3 points)
            max_score += 3
            if value == "Not Found" or (isinstance(value, list) and len(value) == 0):
                factors.append({
                    'factor': 'Value Presence',
                    'status': 'Not Found',
                    'score': 0,
                    'max': 3
                })
                is_missing = True
            else:
                factors.append({
                    'factor': 'Value Presence',
                    'status': 'Found',
                    'score': 3,
                    'max': 3
                })
                score += 3
            
            # Factor 2: Format Validity (0-2 points) - Type-aware regex validation
            max_score += 2
            format_valid = False
            format_score = 0
            
            if not is_missing:
                if isinstance(value, list):
                    value_str = ' '.join(str(v) for v in value)
                    # Check if all items in list match expected format
                    all_valid = True
                    for v in value:
                        if not self._validate_format(str(v), field_type):
                            all_valid = False
                            break
                    if all_valid and len(value) > 0:
                        format_valid = True
                        format_score = 2
                else:
                    value_str = str(value)
                    if self._validate_format(value_str, field_type):
                        format_valid = True
                        format_score = 2
                    elif field_type == 'text' or field_type is None:
                        # For text fields, don't penalize lack of format
                        format_score = 1
                        format_valid = True
            
            if format_valid:
                factors.append({
                    'factor': 'Format Validity',
                    'status': f'Valid {field_type or "text"} format' if format_score == 2 else 'Text format (no validation)',
                    'score': format_score,
                    'max': 2
                })
                score += format_score
            else:
                factors.append({
                    'factor': 'Format Validity',
                    'status': f'Format mismatch for {field_type or "unknown"} type',
                    'score': 0,
                    'max': 2
                })
            
            # Factor 3: Evidence Support (0-2 points)
            max_score += 2
            evidence_score = 0
            
            if not is_missing:
                if isinstance(value, list):
                    value_str = ' '.join(str(v) for v in value)
                else:
                    value_str = str(value)
                
                # Special handling for summarized outputs (e.g., rateDefinition)
                if is_summarized or (field_type == 'text' and 'rate' in str(field_def.get('extractionHint', {}).get('notes', '')).lower()):
                    # Use anchor coverage instead of exact match
                    evidence_score = self._calculate_anchor_coverage(value_str, block_text)
                else:
                    value_lower = value_str.lower()
                    block_lower = block_text.lower()
                    
                    # For numeric/structured values: exact substring match
                    if field_type in ['quantitative_metric', 'date']:
                        if value_lower in block_lower:
                            evidence_score = 2
                        elif self._has_meaningful_tokens(value_str, block_text, stopwords):
                            evidence_score = 1
                    else:
                        # For text values: require meaningful token match
                        if value_lower in block_lower:
                            evidence_score = 2
                        elif self._has_meaningful_tokens(value_str, block_text, stopwords):
                            evidence_score = 1
                
                factors.append({
                    'factor': 'Evidence Support',
                    'status': 'Strong match' if evidence_score == 2 else ('Partial match' if evidence_score == 1 else 'Weak match'),
                    'score': evidence_score,
                    'max': 2
                })
                score += evidence_score
            else:
                factors.append({
                    'factor': 'Evidence Support',
                    'status': 'N/A (value not found)',
                    'score': 0,
                    'max': 2
                })
            
            # Factor 4: Completeness (0-1 point)
            max_score += 1
            completeness_score = 0
            
            if not is_missing:
                if isinstance(value, list):
                    # For lists: sanity check count and structure
                    if len(value) > 0:
                        # Check if it looks like table rows (multiple similar-format items)
                        if len(value) >= 2:
                            # Multiple items suggest table extraction
                            completeness_score = 1
                        elif len(value) == 1:
                            # Single item - check if it's reasonable
                            completeness_score = 0.5
                    else:
                        completeness_score = 0
                else:
                    # For single values: only score if format is valid (not length-based)
                    if format_valid:
                        completeness_score = 1
                    else:
                        completeness_score = 0
                
                factors.append({
                    'factor': 'Completeness',
                    'status': f'{len(value)} item(s)' if isinstance(value, list) else 'Single value',
                    'score': round(completeness_score, 1),
                    'max': 1
                })
                score += completeness_score
            else:
                factors.append({
                    'factor': 'Completeness',
                    'status': 'N/A (value not found)',
                    'score': 0,
                    'max': 1
                })
            
            # Factor 5: Anchor Proximity (0-1 point) - NEW
            max_score += 1
            proximity_score = 0
            
            if not is_missing and pattern_hint:
                proximity_result = self._calculate_anchor_proximity(
                    value_str if not isinstance(value, list) else str(value[0]) if value else '',
                    block_text,
                    pattern_hint
                )
                proximity_score = proximity_result['score']
                anchor_not_found = proximity_result['anchor_not_found']
                
                factors.append({
                    'factor': 'Anchor Proximity',
                    'status': proximity_result['status'],
                    'score': round(proximity_score, 1),
                    'max': 1
                })
                score += proximity_score
            else:
                factors.append({
                    'factor': 'Anchor Proximity',
                    'status': 'N/A (no pattern hint)' if not pattern_hint else 'N/A (value not found)',
                    'score': 0,
                    'max': 1
                })
            
            # Factor 6: Ambiguity Penalty (-0.5 to 0) - NEW
            ambiguity_penalty = 0
            
            if not is_missing and field_type in ['quantitative_metric', 'date', 'duration']:
                ambiguity_result = self._detect_multiple_candidates(
                    value_str if not isinstance(value, list) else str(value[0]) if value else '',
                    block_text,
                    field_type
                )
                multiple_matches = ambiguity_result['count']
                ambiguous_candidates = ambiguity_result['is_ambiguous']
                
                if ambiguous_candidates and multiple_matches > 1:
                    # Apply penalty: -0.5 if multiple candidates found
                    ambiguity_penalty = -0.5
                    factors.append({
                        'factor': 'Ambiguity Check',
                        'status': f'Multiple {field_type} candidates found ({multiple_matches})',
                        'score': round(ambiguity_penalty, 1),
                        'max': 0
                    })
                    score += ambiguity_penalty
                else:
                    factors.append({
                        'factor': 'Ambiguity Check',
                        'status': 'Single candidate or unambiguous',
                        'score': 0,
                        'max': 0
                    })
            else:
                factors.append({
                    'factor': 'Ambiguity Check',
                    'status': 'N/A (not applicable)',
                    'score': 0,
                    'max': 0
                })
            
            # Factor 7: Faithfulness (0-1 point) - NEW for summarized outputs
            faithfulness_score = 0
            
            if not is_missing and is_summarized:
                max_score += 1
                faithfulness_result = self._check_summarized_faithfulness(value_str, block_text)
                faithfulness_score = faithfulness_result['score']
                
                factors.append({
                    'factor': 'Faithfulness',
                    'status': faithfulness_result['status'],
                    'score': round(faithfulness_score, 1),
                    'max': 1
                })
                score += faithfulness_score
            else:
                if is_summarized:
                    max_score += 1
                factors.append({
                    'factor': 'Faithfulness',
                    'status': 'N/A (not summarized output)',
                    'score': 0,
                    'max': 1
                })
            
            # Calculate final confidence level
            if is_missing:
                confidence_level = "Not Present"
                percentage = 0
                display_percentage = 0
            elif max_score == 0:
                confidence_level = "Low"
                percentage = 0
                display_percentage = 0
            else:
                # Ensure score doesn't go negative
                score = max(0, score)
                percentage = (score / max_score) * 100
                # Cap displayed percentage at 95% to avoid false certainty
                display_percentage = min(percentage, 95.0)
                
                if percentage >= 75:
                    confidence_level = "High"
                elif percentage >= 50:
                    confidence_level = "Medium"
                else:
                    confidence_level = "Low"
            
            confidence[field_name] = {
                'level': confidence_level,
                'score': round(score, 1),
                'max_score': max_score,
                'percentage': round(percentage, 1),  # Internal percentage (uncapped)
                'display_percentage': round(display_percentage, 1),  # Display percentage (capped at 95%)
                'factors': factors,
                'isMissing': is_missing,
                'ambiguousCandidates': ambiguous_candidates,
                'multipleMatches': multiple_matches,
                'anchorNotFound': anchor_not_found
            }
        
        return confidence
    
    def _validate_format(self, value_str: str, field_type: str) -> bool:
        """Validate value format based on field type using regex patterns"""
        if not field_type or field_type == 'text':
            return True  # Don't validate text fields
        
        value_str = value_str.strip()
        
        if field_type == 'quantitative_metric':
            # Check for currency, percent, ratio, basis points, or plain numbers
            patterns = [
                r'^\$[\s,]?\d+([,.]\d+)*',  # Currency: $1,000,000 or $ 1000000
                r'USD\s+[\d,]+',  # USD 1,000,000
                r'U\.S\.\s*dollars?\s+[\d,]+',  # U.S. dollars 1,000,000
                r'\d+(\.\d+)?%',  # Percent: 3.5% or 75%
                r'\d+(\.\d+)?:\d+(\.\d+)?',  # Ratio: 3.50:1.00 or 4:1
                r'\d+\.\d+\s*bps',  # Basis points: 150.0 bps
                r'^\d+([,.]\d+)*$',  # Plain number: 1000000 or 1,000,000
            ]
            return any(re.search(pattern, value_str, re.IGNORECASE) for pattern in patterns)
        
        elif field_type == 'date':
            # Check for numeric dates AND month-style dates
            patterns = [
                r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # 01/15/2024 or 2024-01-15
                r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}',  # January 15, 2024
                r'\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}',  # 15 January 2024
            ]
            return any(re.search(pattern, value_str, re.IGNORECASE) for pattern in patterns)
        
        elif field_type == 'location':
            # Check for Section X.XX, Schedule, Exhibit references
            patterns = [
                r'Section\s+[0-9A-Za-z\.()]+',
                r'Schedule\s+[0-9A-Za-z\.()]+',
                r'Exhibit\s+[A-Za-z0-9]+',
                r'Appendix\s+[A-Za-z0-9]+',
            ]
            return any(re.search(pattern, value_str, re.IGNORECASE) for pattern in patterns)
        
        elif field_type == 'duration':
            # Check for duration patterns: "5 days", "30 Business Days", "one month", etc.
            patterns = [
                r'\d+\s+(day|days|Business\s+Day|Business\s+Days|month|months|year|years)',
                r'(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|twenty|thirty|forty|fifty|sixty|ninety)\s+(day|days|Business\s+Day|Business\s+Days|month|months|year|years)',
                r'\d+\s+hour|hours',
            ]
            return any(re.search(pattern, value_str, re.IGNORECASE) for pattern in patterns)
        
        elif field_type == 'boolean':
            # Check for boolean-like values: "Yes", "No", "True", "False", "Automatic", etc.
            boolean_patterns = [
                r'^(yes|no|true|false|automatic|discretionary|required|not\s+required)$',
                r'^(Yes|No|True|False|Automatic|Discretionary)$',
            ]
            value_lower = value_str.lower().strip()
            return any(re.match(pattern, value_lower, re.IGNORECASE) for pattern in boolean_patterns)
        
        return True  # Default: don't penalize unknown types
    
    def _has_meaningful_tokens(self, value_str: str, block_text: str, stopwords: set) -> bool:
        """Check if value has at least 2 meaningful tokens (length > 4, not stopwords) in block"""
        value_lower = value_str.lower()
        block_lower = block_text.lower()
        
        # Extract meaningful tokens (length > 4, not stopwords)
        tokens = [word for word in value_lower.split() 
                  if len(word) > 4 and word not in stopwords]
        
        if len(tokens) < 2:
            return False
        
        # Check if at least 2 meaningful tokens appear in block
        matches = sum(1 for token in tokens if token in block_lower)
        return matches >= 2
    
    def _calculate_anchor_coverage(self, value_str: str, block_text: str) -> int:
        """Calculate anchor coverage for summarized outputs (e.g., rateDefinition)"""
        # Key anchors that should appear in rate definitions
        rate_anchors = [
            'greatest of', 'least of', 'prime rate', 'libor', 'sofr', 'plus', 
            'dividing', 'one minus', 'multiplied by', 'divided by', 'base rate',
            'alternate base rate', 'adjusted', 'applicable', 'margin', 'spread'
        ]
        
        value_lower = value_str.lower()
        block_lower = block_text.lower()
        
        # Count how many anchors from value appear in block
        anchors_found = sum(1 for anchor in rate_anchors 
                           if anchor in value_lower and anchor in block_lower)
        
        # Score based on anchor coverage
        if anchors_found >= 3:
            return 2  # Strong coverage
        elif anchors_found >= 1:
            return 1  # Partial coverage
        else:
            return 0  # Weak coverage
    
    def _calculate_anchor_proximity(self, value_str: str, block_text: str, pattern_hint: str) -> Dict:
        """
        Calculate proximity score based on distance from schema pattern anchor to extracted value.
        
        Returns:
        {
            'score': float (0-1),
            'status': str,
            'anchor_not_found': bool
        }
        """
        try:
            # Find all pattern matches in block
            pattern = pattern_hint.strip('()')  # Remove outer parentheses if present
            # Handle alternation patterns like "(shall mean|means)"
            if pattern.startswith('(') and '|' in pattern:
                # Extract alternatives
                pattern = pattern.strip('()')
                alternatives = [p.strip() for p in pattern.split('|')]
            else:
                alternatives = [pattern]
            
            anchor_positions = []
            for alt_pattern in alternatives:
                # Escape special regex chars but keep intended regex
                # If pattern contains regex metacharacters, use as-is; otherwise escape
                if any(c in alt_pattern for c in ['\\', '(', ')', '[', ']', '.', '*', '+', '?', '^', '$']):
                    # Looks like regex, use as-is
                    matches = list(re.finditer(alt_pattern, block_text, re.IGNORECASE))
                else:
                    # Literal string, escape it
                    escaped = re.escape(alt_pattern)
                    matches = list(re.finditer(escaped, block_text, re.IGNORECASE))
                
                for match in matches:
                    anchor_positions.append(match.start())
            
            if not anchor_positions:
                return {
                    'score': 0,
                    'status': 'Anchor pattern not found in block',
                    'anchor_not_found': True
                }
            
            # Find value position in block
            value_lower = value_str.lower()
            block_lower = block_text.lower()
            value_pos = block_lower.find(value_lower)
            
            if value_pos == -1:
                # Value not found as exact substring, try to find closest match
                # Extract first meaningful token from value
                value_tokens = value_str.split()
                if value_tokens:
                    first_token = value_tokens[0].lower()
                    value_pos = block_lower.find(first_token)
            
            if value_pos == -1:
                return {
                    'score': 0,
                    'status': 'Value not found near anchor',
                    'anchor_not_found': False
                }
            
            # Calculate minimum distance to any anchor
            min_distance = min(abs(value_pos - anchor_pos) for anchor_pos in anchor_positions)
            
            # Score based on proximity: within 500 chars = full score, degrades linearly
            proximity_threshold = 500
            if min_distance <= proximity_threshold:
                # Linear decay from 1.0 to 0.0
                score = max(0, 1.0 - (min_distance / proximity_threshold))
                if min_distance <= 100:
                    status = f'Very close to anchor ({min_distance} chars)'
                elif min_distance <= 250:
                    status = f'Close to anchor ({min_distance} chars)'
                else:
                    status = f'Moderate distance from anchor ({min_distance} chars)'
            else:
                score = 0
                status = f'Far from anchor ({min_distance} chars)'
            
            return {
                'score': round(score, 2),
                'status': status,
                'anchor_not_found': False
            }
        except Exception as e:
            # If pattern matching fails, return neutral score
            return {
                'score': 0,
                'status': f'Pattern matching error: {str(e)[:50]}',
                'anchor_not_found': True
            }
    
    def _detect_multiple_candidates(self, value_str: str, block_text: str, field_type: str) -> Dict:
        """
        Detect if block contains multiple values of the same format class as extracted value.
        
        Returns:
        {
            'count': int,
            'is_ambiguous': bool
        }
        """
        if not value_str or value_str == "Not Found":
            return {'count': 0, 'is_ambiguous': False}
        
        # Extract format pattern from value
        if field_type == 'quantitative_metric':
            # Find all currency, percent, ratio, or number patterns
            patterns = [
                r'\$[\s,]?\d+([,.]\d+)*',  # Currency
                r'USD\s+[\d,]+',
                r'U\.S\.\s*dollars?\s+[\d,]+',
                r'\d+(\.\d+)?%',  # Percent
                r'\d+(\.\d+)?:\d+(\.\d+)?',  # Ratio
                r'\d+\.\d+\s*bps',  # Basis points
                r'\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b',  # Large numbers with commas
            ]
        elif field_type == 'date':
            patterns = [
                r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # Numeric dates
                r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}',  # Month-style
            ]
        elif field_type == 'duration':
            patterns = [
                r'\d+\s+(day|days|Business\s+Day|Business\s+Days|month|months|year|years)',
                r'(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|twenty|thirty|forty|fifty|sixty|ninety)\s+(day|days|Business\s+Day|Business\s+Days|month|months|year|years)',
            ]
        else:
            return {'count': 0, 'is_ambiguous': False}
        
        # Find all matches in block
        all_matches = set()
        for pattern in patterns:
            matches = re.findall(pattern, block_text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = ' '.join(match)
                all_matches.add(match.strip())
        
        count = len(all_matches)
        is_ambiguous = count > 1
        
        return {
            'count': count,
            'is_ambiguous': is_ambiguous
        }
    
    def _check_summarized_faithfulness(self, value_str: str, block_text: str) -> Dict:
        """
        Check if summarized output is faithful to source:
        1. Summary must not contain numeric tokens not present in block
        2. Summary must include at least one key base-rate term from block
        
        Returns:
        {
            'score': float (0-1),
            'status': str
        }
        """
        value_lower = value_str.lower()
        block_lower = block_text.lower()
        
        # Extract numeric tokens from value and block
        value_numbers = set(re.findall(r'\d+(?:\.\d+)?', value_str))
        block_numbers = set(re.findall(r'\d+(?:\.\d+)?', block_text))
        
        # Check 1: All numbers in value must appear in block
        numbers_faithful = True
        introduced_numbers = []
        for num in value_numbers:
            if num not in block_numbers:
                # Check if it's a close match (e.g., "1.00" vs "1.0")
                close_match = False
                for block_num in block_numbers:
                    try:
                        if abs(float(num) - float(block_num)) < 0.01:
                            close_match = True
                            break
                    except:
                        pass
                if not close_match:
                    numbers_faithful = False
                    introduced_numbers.append(num)
        
        # Check 2: At least one key rate term must appear
        key_rate_terms = [
            'prime rate', 'libor', 'sofr', 'federal funds', 'base rate',
            'alternate base rate', 'adjusted libo', 'eurodollar', 'cd rate'
        ]
        has_rate_term = any(term in value_lower and term in block_lower for term in key_rate_terms)
        
        # Score based on both checks
        if numbers_faithful and has_rate_term:
            score = 1.0
            status = 'Faithful: all numbers present, key terms included'
        elif numbers_faithful and not has_rate_term:
            score = 0.5
            status = 'Partially faithful: numbers OK but missing key rate terms'
        elif not numbers_faithful and has_rate_term:
            score = 0.3
            status = f'Partially faithful: key terms OK but introduced numbers: {", ".join(introduced_numbers[:3])}'
        else:
            score = 0.0
            status = f'Not faithful: introduced numbers and missing key terms'
        
        return {
            'score': score,
            'status': status
        }

