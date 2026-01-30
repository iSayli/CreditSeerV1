import os
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
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    
    def extract(self, block: Dict, chunk_type: str, schema: Dict) -> Dict:
        """
        Extract values from a Stage 1 block
        
        Returns:
        {
            'blockId': str,
            'valueType': str,
            'values': Dict
        }
        """
        block_id = block.get('blockId')
        value_type = block.get('valueType')
        block_text = block.get('text', '')
        
        if not block_text or block_text == 'Not Found':
            return {
                'blockId': block_id,
                'valueType': value_type,
                'values': {}
            }
        
        # Get schema section for this valueType
        value_type_schema = self._get_value_type_schema(schema, value_type)
        if not value_type_schema:
            return {
                'blockId': block_id,
                'valueType': value_type,
                'values': {}
            }
        
        # Build prompt
        prompt = self._build_prompt(block_id, block_text, value_type, value_type_schema)
        
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
        return {
            'blockId': block_id,
            'valueType': value_type,
            'values': values
        }
    
    def _get_value_type_schema(self, schema: Dict, value_type: str) -> Dict:
        """Get schema section for specific valueType"""
        if 'schemasByValueType' in schema:
            return schema['schemasByValueType'].get(value_type, {})
        return {}
    
    def _build_prompt(self, block_id: str, block_text: str, value_type: str, value_type_schema: Dict) -> str:
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

