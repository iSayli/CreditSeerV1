import os
from openai import OpenAI
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv()

class Stage1Extractor:
    """Stage 1: Extract block-level text with valueType assignment"""
    
    def __init__(self):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    
    def extract(self, text_chunk: str, chunk_type: str, schema: Dict) -> List[Dict]:
        """
        Extract blocks from chunk using Stage 1 schema
        
        Returns list of blocks:
        {
            'blockId': str,
            'valueType': str,
            'text': str
        }
        """
        # Build prompt
        prompt = self._build_prompt(text_chunk, chunk_type, schema)
        
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
        blocks = self._parse_output(output_text, schema)
        
        return blocks
    
    def _build_prompt(self, text_chunk: str, chunk_type: str, schema: Dict) -> str:
        """Build Stage 1 extraction prompt"""
        # Convert schema to string format
        schema_str = self._format_schema_for_prompt(schema)
        
        prompt = f"""You are an expert legal document analyst specializing in credit agreements.

Your task is to IDENTIFY AND ISOLATE legally meaningful text blocks from the provided document chunk.

This is STAGE 1 of a two-stage extraction system.

────────────────────────────────────────
CRITICAL RULES (STAGE 1)
────────────────────────────────────────
1. Extract ONLY text that is explicitly present in the chunk. Never hallucinate.
2. Do NOT extract individual values (dates, amounts, ratios, etc.).
3. Your goal is ONLY to extract full, verbatim BLOCK TEXT.
4. Extract ONLY the blocks defined in the schema.
5. If a block is not present in the chunk, return "Not Found" for that block.
6. Always prioritize semantic meaning over exact pattern matching.
7. A block may also contain a table or schedule following the text.
8. A block may also contain a formula or multi-part calculation following the text.
9. A block may also contain a conditional clause or sentence following the text.
10. A block may also contain a list of items following the text.
11. A block may also have spacing between the text and the table or schedule.
12. A block ends ONLY when a new section or covenant begins.

────────────────────────────────────────
BLOCK IDENTIFICATION GUIDANCE
────────────────────────────────────────
• Anchor patterns are provided as hints and may appear in different forms.
• Use semantic equivalents, nearby definitions, and functional descriptions.
• Do NOT rely on section numbers.
• A block may span multiple sentences or paragraphs.
• Column headers such as "Last day of Test Period" do NOT indicate a new block.
• Tables and schedules following phrases like "set forth below" are part of the same block.
• Do NOT stop extraction at the start of a table.


────────────────────────────────────────
OUTPUT REQUIREMENTS
────────────────────────────────────────
For EACH block defined in the schema, output exactly one entry using this format:

BlockId: <blockId>
ValueType: <valueType>
BlockText: <verbatim extracted text or "Not Found">

• Do NOT include explanations.
• Do NOT include JSON.
• Do NOT include commentary.
• Preserve original wording exactly as written.

────────────────────────────────────────
ILLUSTRATIVE EXAMPLE
────────────────────────────────────────
Example block:

SECTION XYZ. Example Covenant
Commencing with the fiscal quarter ending Example Date, the Borrower shall not
permit the Example Covenant, in each case on the last day of any Test Period,
to be greater than the Example Threshold set forth below opposite such last day:

Last day of Test Period     Example Threshold
Example Date 1                Example Threshold Value 1
Example Date 2                Example Threshold Value 2
Example Date 3                Example Threshold Value 3

Output:
BlockId: Example Covenant
ValueType: covenant
BlockText: SECTION XYZ. Example Covenant
Commencing with the fiscal quarter ending Example Date, the Borrower shall not
permit the Example Covenant, in each case on the last day of any Test Period,
to be greater than the Example Threshold set forth below opposite such last day:

Last day of Test Period     Example Threshold
Example Date 1                Example Threshold Value 1
Example Date 2                Example Threshold Value 2
Example Date 3                Example Threshold Value 3

────────────────────────────────────────
SCHEMA CONTEXT
────────────────────────────────────────
Chunk Type: {chunk_type}

STAGE 1 SCHEMA:
{schema_str}

────────────────────────────────────────
DOCUMENT CHUNK
────────────────────────────────────────
{text_chunk}

────────────────────────────────────────
BEGIN STAGE 1 EXTRACTION
────────────────────────────────────────"""
        
        return prompt
    
    def _format_schema_for_prompt(self, schema: Dict) -> str:
        """Format schema JSON for prompt"""
        # Handle different schema structures
        if 'targets' in schema:
            # Cover page schema
            blocks = schema['targets']
        elif 'blocks' in schema:
            # Standard block schema
            blocks = schema['blocks']
        elif 'blockTemplates' in schema:
            # Negative covenants schema
            blocks = schema['blockTemplates']
        else:
            return str(schema)
        
        schema_lines = []
        for block in blocks:
            block_id = block.get('blockId') or block.get('fieldId', '')
            value_type = block.get('valueType', '')
            anchor = block.get('anchorPattern', '')
            label = block.get('label', '')
            
            schema_lines.append(f"BlockId: {block_id}")
            schema_lines.append(f"Label: {label}")
            schema_lines.append(f"ValueType: {value_type}")
            schema_lines.append(f"AnchorPattern: {anchor}")
            schema_lines.append("")
        
        return "\n".join(schema_lines)
    
    def _parse_output(self, output_text: str, schema: Dict) -> List[Dict]:
        """Parse LLM output into structured blocks with multiline BlockText support"""
        blocks = []
        
        # Extract block information
        current_block = {}
        collecting_text = False
        lines = output_text.split('\n')
        
        for line in lines:
            original_line = line  # Preserve original for multiline text
            line_stripped = line.strip()
            
            # Check for new block start
            if line_stripped.startswith('BlockId:'):
                # Save previous block if exists
                if current_block:
                    blocks.append(current_block)
                
                # Start new block
                block_id = line_stripped.replace('BlockId:', '').strip()
                current_block = {'blockId': block_id}
                collecting_text = False
            
            elif line_stripped.startswith('ValueType:'):
                value_type = line_stripped.replace('ValueType:', '').strip()
                if current_block:
                    current_block['valueType'] = value_type
                collecting_text = False
            
            elif line_stripped.startswith('BlockText:'):
                # Start collecting multiline text
                block_text = line_stripped.replace('BlockText:', '').strip()
                if current_block:
                    current_block['text'] = block_text
                    collecting_text = True
            
            elif collecting_text:
                # Continue collecting text until next BlockId or empty line that signals block end
                # Only stop if we see a new BlockId (which we already handled above)
                # Preserve original line formatting (including empty lines within the block)
                if current_block and 'text' in current_block:
                    # Append with newline to preserve structure
                    if current_block['text']:
                        current_block['text'] += "\n" + original_line
                    else:
                        current_block['text'] = original_line
            
            # Handle empty lines - don't break text collection, but preserve them
            elif not line_stripped and collecting_text:
                if current_block and 'text' in current_block:
                    current_block['text'] += "\n"
        
        # Add final block
        if current_block:
            blocks.append(current_block)
        
        return blocks

