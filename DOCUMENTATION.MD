# CreditSeer - Complete Documentation

## Table of Contents
1. [Application Summary](#application-summary)
2. [How the Application Works](#how-the-application-works)
3. [Limitations](#limitations)
4. [Architecture Overview](#architecture-overview)
5. [Project Structure](#project-structure)
6. [Component Breakdown](#component-breakdown)
7. [Data Flow](#data-flow)
8. [Key Functionality](#key-functionality)
9. [Configuration Files](#configuration-files)
10. [API Documentation](#api-documentation)
11. [Frontend Documentation](#frontend-documentation)

---

## Application Summary

### What It Does
**CreditSeer** is an AI-powered application that automates the extraction of structured data from credit agreement PDF documents using a **two-stage, schema-driven LLM architecture**. The system processes lengthy legal documents (often 100+ pages) through a multi-stage pipeline: PDF text extraction, intelligent chunking by articles, Stage 1 block discovery, and Stage 2 value extraction with confidence scoring. Instead of manually reading through complex credit agreements, users can upload a PDF and receive structured, extracted data organized by document sections with detailed confidence metadata.

### Key Benefits
- **Two-Stage Extraction**: Separates block discovery from value extraction to minimize hallucination and cross-term contamination
- **Comprehensive Processing**: Extracts text from all pages including headers, footers, and page numbers
- **Intelligent Chunking**: Automatically identifies and chunks documents by articles using Table of Contents parsing
- **Table Handling**: Detects and merges fragmented tables that are common in legal PDFs
- **Schema-Driven Extraction**: Uses predefined JSON schemas to extract structured data with anti-hallucination measures
- **Confidence Scoring**: Multi-factor confidence calculation (7 factors) with detailed breakdowns for each extracted value
- **Block Skipping Optimization**: Automatically skips Stage 2 extraction for blocks not found in Stage 1, reducing LLM calls by ~42%
- **Step-Driven Workflow**: Upload → Process → Chunk → Stage 1 → Stage 2 workflow ensures accurate data extraction
- **Transparency**: Provides full extracted text, chunk metadata, block text, and confidence factors for verification

### Use Cases
- Legal due diligence on credit agreements
- Financial analysis and covenant monitoring
- Compliance reviews and risk assessment
- Contract comparison across multiple agreements
- Automated data extraction for credit analysis systems
- Confidence-based quality assurance for extracted values

---

## How the Application Works

This section explains the step-by-step process the application follows in simple, easy-to-understand language.

### Step-by-Step Process

#### Step 1: You Upload a PDF File
You open the web application in your browser and select a credit agreement PDF file from your computer. The file needs to be a PDF - other file types won't work. Once you select the file, it's automatically uploaded to the server and assigned a unique file ID. The application resets any previous state to ensure a clean working environment.

#### Step 2: The Server Validates Your File
The backend server receives your file and makes sure it's actually a PDF. If it's not a PDF file, you'll get an error message telling you to upload a PDF instead. The file is saved to the server with a unique UUID-based filename. Old uploaded files are automatically cleaned up to ensure privacy.

#### Step 3: The PDF Gets Processed
After upload, you click the "Process PDF" button. This step extracts all text and tables from the document. The system uses a sophisticated dual-method approach:

**Method 1: Standard Text Extraction**
- Uses `pdfplumber`'s built-in text extraction
- Captures main document content efficiently

**Method 2: Word-Based Extraction**
- Extracts individual words with precise coordinates
- Captures text in headers, footers, and page numbers that standard extraction might miss
- Sorts words by position and reconstructs text preserving line structure

**Table Detection and Merging:**
- Detects tables using line-based strategy
- Automatically merges fragmented tables (common in legal PDFs where one logical table is split into multiple one-row tables)
- Preserves table structure and formatting

**Result**: You get complete extracted text with all tables properly formatted, including page markers (`--- Page X ---`) to preserve document structure.

#### Step 4: You Chunk the Text
Once processing is complete, you click the "Chunk Text" button. The application then:

1. **Parses the Table of Contents**: Identifies all articles (e.g., "ARTICLE I DEFINITIONS", "ARTICLE II THE CREDITS") and their page numbers
2. **Finds Article Headers in Text**: Instead of relying on page numbers (which can be inconsistent), it searches for article headers directly in the extracted text
3. **Classifies Chunk Types**: Each chunk is classified (e.g., `definitions`, `credits`, `negative_covenants`, `events_of_default`)
4. **Creates Chunks**: Divides the document into logical sections:
   - **Chunk 1**: Cover Page (everything before the first article)
   - **Chunks 2-N**: Each article becomes its own chunk with a `chunkType`

**Why This Works:**
- No dependency on page number offsets
- Works even if page numbers are inconsistent
- Handles different TOC formats
- More accurate than page-based mapping
- Semantic classification enables proper schema routing

#### Step 5: Stage 1 - Block Discovery
You click the "Run Stage 1" button. For each chunk that has a Stage 1 schema, the system:

1. **Loads the Stage 1 Schema**: Matches the chunk's `chunkType` to the appropriate schema (e.g., `definitions.stage1.json`)
2. **Sends to LLM**: Creates a prompt with the schema's block definitions (anchor patterns, labels, valueTypes)
3. **LLM Identifies Blocks**: The AI locates each block using anchor patterns and semantic matching
4. **Extracts Block Text**: For each block found, extracts the **entire verbatim text** (including tables, formulas, multi-paragraph content)
5. **Assigns ValueType**: Each block gets a `valueType` (e.g., `commitment`, `covenant`, `fee`, `eventOfDefault`)
6. **Returns "Not Found"**: If a block isn't present, returns `"Not Found"` for that block

**Result**: You see a list of blocks for each chunk, with full block text that can be expanded to view. Each block has a `blockId`, `valueType`, and `text`.

#### Step 6: Stage 2 - Value Extraction with Confidence
You click the "Run Stage 2" button. For each block that was found in Stage 1:

1. **Skips Missing Blocks**: Blocks marked `"Not Found"` in Stage 1 are automatically skipped (no LLM call made)
2. **Loads Stage 2 Schema**: Matches the block's `valueType` to the appropriate schema section
3. **Sends to LLM**: Creates a prompt with field definitions, extraction hints, and the block text
4. **LLM Extracts Values**: The AI extracts structured values from the block text only
5. **Calculates Confidence**: For each extracted value, calculates confidence using 7 factors:
   - Value Presence (0-3 points)
   - Format Validity (0-2 points)
   - Evidence Support (0-2 points)
   - Completeness (0-1 point)
   - Anchor Proximity (0-1 point)
   - Ambiguity Penalty (-0.5 to 0)
   - Faithfulness (0-1 point, for summarized outputs)
6. **Returns Results**: Structured values with confidence levels (High/Medium/Low/Not Present) and detailed factor breakdowns

**Result**: You see extracted values organized by block, with confidence levels and expandable details showing how confidence was calculated.

#### Step 7: You Review the Results
The results appear on your screen showing:
- **Cover Page Data**: Agreement details, parties, dates
- **Definitions Data**: Facility commitments, maturity dates, pricing terms, rate definitions
- **Covenants Data**: Financial ratios, thresholds, test periods
- **Credits Data**: Fees, interest rates, payment timing
- **Events of Default Data**: Default categories, grace periods, remedies

Each extraction result includes:
- The chunk and block it came from
- All extracted fields with their values
- Confidence level and percentage (capped at 95% to avoid false certainty)
- Detailed confidence factors (expandable)
- Ambiguity flags (if multiple candidates found)

#### Step 8: What If Something Goes Wrong?
If anything fails during the process, you'll see a clear error message explaining what went wrong. Common issues include:
- File isn't a PDF
- PDF is corrupted or can't be read
- AI API is unavailable or API key is missing
- Document structure is too unusual (e.g., no Table of Contents)
- Chunking fails if TOC cannot be parsed
- Connection errors during LLM calls

### The Whole Process in One Sentence
**You upload a PDF → The app extracts all text and tables → You chunk the text by articles → You run Stage 1 to discover blocks → You run Stage 2 to extract values with confidence → You see organized results with confidence metadata.**

---

## Limitations

This section details the current limitations and constraints of the application. Understanding these limitations helps set realistic expectations and identify areas for future improvement.

### PDF Processing Limitations

#### 1. Text and Table Extraction Only
- **What it means**: The application extracts text and tables from PDFs, but images, diagrams, charts, and scanned documents are not processed.
- **Impact**: 
  - If important information is only in an image or diagram, it won't be extracted
  - Scanned PDFs (where text is actually an image) won't work unless they've been OCR'd (Optical Character Recognition) processed
- **Example**: A commitment amount written in a chart image won't be found, even if it's visible to human readers.

#### 2. Table Structure Simplification
- **What it means**: While tables are detected and merged, complex nested table structures may be simplified when converted to text format.
- **Impact**:
  - Very complex financial tables with multiple levels of nesting may lose some structure
  - Table formatting is preserved but may not perfectly match the original layout
- **Example**: A table with merged cells or complex formatting might be flattened.

#### 3. Formatting Information Lost
- **What it means**: While page markers are preserved, other formatting (bold, italics, font sizes, colors) is stripped away during text extraction.
- **Impact**:
  - Emphasis through formatting is invisible to the AI
  - Document structure is preserved through page markers and article headers
- **Example**: Important terms highlighted in bold won't stand out anymore - they're just regular text.

#### 4. Complex Layout Handling
- **What it means**: PDFs with very complex layouts (multi-column text, text boxes, annotations, overlays) may extract text in a slightly different order.
- **Impact**:
  - Text might appear out of sequence in rare cases
  - Sidebars or margin notes might interfere with main content
- **Example**: A definition in the margin might be read as part of the main paragraph.

#### 5. Password-Protected PDFs
- **What it means**: Encrypted or password-protected PDFs cannot be processed.
- **Impact**: Any PDF that requires a password to open will fail completely.
- **Solution needed**: PDF decryption would need to be implemented, or users must provide unlocked PDFs.

### Document Processing Limitations

#### 6. Chunk Text Length Limit
- **What it means**: Chunks are limited to 150,000 characters when sent to the AI for analysis.
- **Impact**:
  - Very long articles (over ~30-40 pages typically) will have their later portions truncated
  - Information that appears later in a very long chunk won't be extracted
- **Why this limit exists**: 
  - Token limits for AI API calls (more text = more cost)
  - Processing speed concerns
  - API response time considerations
- **Example**: If a covenant definition is only mentioned at the end of a very long Negative Covenants article, it might not be found if that section falls after the 150,000 character limit.

#### 7. Table of Contents Dependency
- **What it means**: The chunking process requires a parseable Table of Contents in the document.
- **Impact**:
  - Documents without a TOC cannot be chunked automatically
  - Unusual TOC formats might not be recognized
  - Chunking will fail if TOC cannot be parsed
- **Workaround**: Manual chunking or processing entire document as one chunk would need to be implemented.

### AI Processing Limitations

#### 8. Dependency on OpenAI API
- **What it means**: The application requires an active internet connection and a valid OpenAI API key. It cannot work offline.
- **Impact**:
  - If OpenAI's service is down, extraction won't work
  - API costs apply for each extraction
  - Rate limits may apply (requests per minute/hour)
  - Privacy concerns: documents are sent to a third-party service
- **Cost consideration**: Each chunk extraction costs money based on OpenAI's pricing. Processing many documents can become expensive. However, block skipping optimization reduces costs by ~42%.

#### 9. Model Accuracy Limitations
- **What it means**: The AI model (GPT-4o-mini) is not perfect and may make mistakes.
- **Impact**:
  - Some fields might be extracted incorrectly
  - Values might be misread or misinterpreted
  - Context might be misunderstood
  - False positives (finding things that aren't there)
  - False negatives (missing things that are there)
- **Example**: The AI might confuse a "Maximum Commitment" with an "Initial Commitment" if both appear in the document.

#### 10. No Learning or Memory
- **What it means**: Each document is analyzed independently. The AI doesn't learn from previous analyses or remember patterns across documents.
- **Impact**:
  - Can't improve accuracy based on user corrections
  - Can't detect patterns across multiple agreements
  - Each analysis starts from scratch
- **Potential improvement**: Could implement feedback loops or fine-tuning based on corrections.

#### 11. Schema Dependency
- **What it means**: The application relies heavily on predefined JSON schemas which describe what to extract.
- **Impact**:
  - Non-standard agreement formats might confuse the AI
  - Unusual document structures may result in missed fields
  - The schemas need manual updates for new document types or fields
- **Example**: If an agreement uses completely different terminology or structure, the AI might search in the wrong places or miss fields.

#### 12. Sequential Processing
- **What it means**: Chunks and blocks are processed sequentially, not in parallel.
- **Impact**:
  - Slower processing times for documents with many chunks
  - Not utilizing available computational resources efficiently
- **Potential improvement**: Could implement parallel processing for multiple chunks/blocks.

### Functional Limitations

#### 13. Single Document Processing
- **What it means**: Only one PDF can be processed at a time through the web interface.
- **Impact**:
  - Can't analyze multiple documents simultaneously
  - No batch processing capability
  - Slow for processing many documents
- **Workaround**: Users must upload and process documents one by one.

#### 14. No Result Storage
- **What it means**: Results are not saved anywhere. Once you refresh the page or close the browser, results are lost.
- **Impact**:
  - Can't compare results over time
  - Can't access previous analyses
  - No historical record
- **Potential improvement**: Database storage or local storage could be added.

#### 15. No Export Functionality
- **What it means**: Results can only be viewed in the browser. There's no way to export to Excel, CSV, JSON, or other formats.
- **Impact**:
  - Results must be manually copied if needed elsewhere
  - Can't integrate with other tools or workflows
  - Difficult to share results in structured formats
- **Potential improvement**: Add export to CSV, Excel, or JSON functionality.

#### 16. No Custom Schemas
- **What it means**: The schemas are fixed and defined in JSON files. Users cannot customize what to extract without code changes.
- **Impact**:
  - Can't add custom fields without modifying schema files
  - Can't remove fields you don't care about
  - One-size-fits-all approach
- **Potential improvement**: Allow users to customize schemas or select which fields to extract.

#### 17. Confidence Calculation Limitations
- **What it means**: Confidence scores are heuristic-based and may not always reflect ground truth accuracy.
- **Impact**:
  - High confidence doesn't guarantee correctness
  - Some false positives may have high confidence
  - Confidence capped at 95% to avoid false certainty, but this is still a heuristic
- **Example**: A value might have 95% confidence but still be wrong if it's the wrong instance among multiple similar values.

### User Experience Limitations

#### 18. No Progress Indication for Long Documents
- **What it means**: While processing, users see status messages but no detailed progress bar or time estimate for each stage.
- **Impact**:
  - Users don't know how long processing will take
  - Can't tell if the application has frozen on very long documents
  - Poor user experience for large documents
- **Potential improvement**: Add progress indicators and time estimates for each stage.

#### 19. No Error Recovery
- **What it means**: If processing fails partway through, there's no partial results or ability to retry just the failed parts.
- **Impact**:
  - Must restart entire analysis if something fails
  - Wasted time and API costs on failed attempts
- **Potential improvement**: Implement checkpointing and partial result recovery.

#### 20. No User Authentication
- **What it means**: The application has no login system or user accounts.
- **Impact**:
  - No way to track who analyzed what
  - No access control
  - No audit trail
  - Results can't be associated with specific users

#### 21. No Collaboration Features
- **What it means**: Multiple users can't work together or share results.
- **Impact**:
  - Must manually share results
  - No commenting or annotation features
  - No team workflows

### Technical Limitations

#### 22. Single-User Architecture
- **What it means**: The application is designed for one user at a time. No concurrent user handling.
- **Impact**:
  - Performance degrades with multiple simultaneous users
  - No load balancing or scaling mechanisms
  - Not suitable for production multi-user environments

#### 23. No Caching
- **What it means**: Every request processes the document from scratch, even if it was analyzed before.
- **Impact**:
  - Wasted computational resources
  - Higher API costs
  - Slower response times for repeated analyses
- **Potential improvement**: Implement caching for previously analyzed documents.

#### 24. Hardcoded Configuration
- **What it means**: Many settings (like the 150,000 character limit, model selection, temperature) are hardcoded or only changeable via environment variables.
- **Impact**:
  - Users can't customize processing parameters
  - Requires code changes or server access to adjust settings
  - No user-facing configuration options

#### 25. Error Messages Could Be More Helpful
- **What it means**: Some error messages are technical and not user-friendly.
- **Impact**:
  - Users might not understand what went wrong
  - Difficult to troubleshoot issues
  - Poor user experience when things fail

### Security and Privacy Limitations

#### 26. No Data Encryption in Transit (by default)
- **What it means**: While HTTPS should be used in production, the development setup uses HTTP.
- **Impact**:
  - Sensitive financial documents could be intercepted
  - Privacy concerns with unencrypted data transmission

#### 27. Documents Sent to Third-Party Service
- **What it means**: PDF contents are sent to OpenAI's servers for processing.
- **Impact**:
  - Privacy concerns with sensitive financial documents
  - Compliance issues (e.g., GDPR, financial regulations)
  - No control over how OpenAI handles the data
  - May violate organizational data policies

#### 28. No Document Retention Policy
- **What it means**: While results aren't stored, uploaded PDFs are stored on the server temporarily. There's automatic cleanup of old files, but no explicit retention policy.
- **Impact**:
  - Uncertainty about data retention
  - Potential compliance issues
  - Storage space concerns over time

### Performance Limitations

#### 29. Synchronous Processing
- **What it means**: The entire analysis happens in one request chain. The browser waits for each stage to complete.
- **Impact**:
  - Long wait times for large documents
  - Browser may timeout on very long analyses
  - Poor user experience during processing
- **Potential improvement**: Implement asynchronous processing with job queues.

#### 30. LLM Call Count
- **What it means**: Each document requires multiple LLM calls (Stage 1: ~6 calls, Stage 2: ~17-34 calls depending on blocks found).
- **Impact**:
  - Higher API costs for documents with many blocks
  - Longer processing times
  - Rate limiting concerns
- **Mitigation**: Block skipping optimization reduces Stage 2 calls by ~42% when blocks are not found.

### Summary of Limitations

**Critical Limitations:**
- Chunks limited to 150,000 characters (very long articles may be truncated)
- Requires Table of Contents for chunking (documents without TOC fail)
- Requires internet and OpenAI API (can't work offline)
- No result storage or export functionality
- Single document processing only
- Confidence scores are heuristic-based, not ground truth

**Important Limitations:**
- AI accuracy is not perfect (may make mistakes)
- No validation of extracted values beyond format checks
- Privacy concerns (documents sent to third-party)
- No custom schemas
- Schema-dependent (may struggle with non-standard formats)
- Sequential processing (not parallelized)

**Minor Limitations:**
- No progress indicators
- Limited error recovery
- No user accounts or collaboration features
- No comparison or benchmarking tools

Understanding these limitations helps users:
- Set appropriate expectations
- Know when the application might not be suitable
- Identify documents that may need manual review
- Plan for potential inaccuracies or missing data

---

## Architecture Overview

### Technology Stack

**Backend:**
- **Framework**: Flask (Python)
- **LLM Integration**: OpenAI GPT-4o-mini
- **PDF Processing**: pdfplumber, PyPDF2 (fallback)
- **Server**: Flask development server (port 5001)

**Frontend:**
- **Framework**: Vanilla HTML/CSS/JavaScript
- **Styling**: Modern CSS with component-based design
- **No Build Step**: Direct HTML file served by Flask

### System Architecture
```
┌─────────────┐         HTTP POST          ┌─────────────┐
│   Browser   │───────────────────────────>│    Flask    │
│  (HTML/JS)   │         /api/*             │   Backend   │
│             │<───────────────────────────│             │
└─────────────┘      JSON Response         └──────┬──────┘
                                                   │
                              ┌────────────────────┼────────────────────┐
                              │                    │                    │
                    ┌─────────▼────────┐  ┌───────▼───────┐  ┌────────▼────────┐
                    │   PDF Processor  │  │  LLM Client   │  │   Schema Loader │
                    │   (pdfplumber)   │  │   (OpenAI)    │  │   (JSON files)  │
                    └──────────────────┘  └───────────────┘  └─────────────────┘
                              │
                    ┌─────────▼────────┐
                    │   Text Chunker   │
                    │  (TOC Parser)    │
                    └──────────────────┘
                              │
                    ┌─────────▼────────┐
                    │ Stage 1 Extractor│
                    │  (Block Discovery)│
                    └──────────────────┘
                              │
                    ┌─────────▼────────┐
                    │ Stage 2 Extractor│
                    │ (Value Extraction)│
                    └──────────────────┘
```

### Two-Stage Extraction Architecture

**Stage 1: Block Discovery**
- Input: Chunk text + Stage 1 schema
- Process: LLM identifies and extracts block-level text
- Output: Blocks with `blockId`, `valueType`, and `text`
- Purpose: Isolate legally meaningful text blocks before value extraction

**Stage 2: Value Extraction**
- Input: Stage 1 blocks + Stage 2 schema
- Process: LLM extracts structured values from block text only
- Output: Field-value pairs with confidence metadata
- Purpose: Extract precise values with confidence scoring
- Optimization: Skips blocks marked "Not Found" in Stage 1

---

## Project Structure

### Directory Tree
```
CreditSeerV1/
├── app.py                      # Flask application entry point
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (not in git)
├── .gitignore                  # Git ignore rules
├── README.md                   # Quick start guide
├── DOCUMENTATION.MD            # This file
├── run.sh                      # Server startup script
│
├── pdf_processing/             # PDF processing utilities
│   ├── __init__.py
│   └── processor.py           # Core PDF extraction with table merging
│
├── chunking/                   # Text chunking utilities
│   ├── __init__.py
│   └── chunker.py             # TOC parsing and article-based chunking
│
├── extraction/                 # Data extraction utilities
│   ├── __init__.py
│   ├── stage1_extractor.py    # Stage 1: Block discovery
│   └── stage2_extractor.py    # Stage 2: Value extraction + confidence
│
├── schemas/                    # Schema loading utilities
│   ├── __init__.py
│   └── schema_loader.py       # Schema loading and mapping
│
├── schema/                     # Schema definitions for extraction
│   ├── cover.stage1.json      # Cover page schema (Stage 1)
│   ├── definitions.stage1.json
│   ├── definitions.stage2.json
│   ├── representations.stage1.json
│   ├── negativeCovenants.stage1.json
│   ├── negativeCovenants.stage2.json
│   ├── credits.stage1.json
│   ├── credits.stage2.json
│   ├── eventsOfDefault.stage1.json
│   └── eventsOfDefault.stage2.json
│
├── uploads/                    # Uploaded PDF files (gitignored)
│
└── frontend/                   # Frontend application
    └── index.html             # Single-page application UI
```

---

## Component Breakdown

### Backend Components

#### 1. `app.py`
**Purpose**: Flask application initialization and route handling

**Key Responsibilities:**
- Creates the Flask application instance
- Configures CORS middleware for frontend communication
- Loads environment variables (`.env` file)
- Defines API routes for all stages
- Manages global application state
- Handles file cleanup and state reset

**Key Features:**
- **CORS Configuration**: Allows requests from frontend
- **Environment Variables**: Reads `OPENAI_API_KEY` from `.env`
- **Global State**: In-memory storage for chunks, Stage 1 results, Stage 2 results
- **File Cleanup**: Automatic cleanup of old uploaded files
- **State Reset**: Resets state on new upload or explicit reset

**API Routes:**
- `GET /` - Serves frontend HTML
- `GET /api/health` - Health check endpoint
- `POST /api/upload` - File upload
- `POST /api/process-pdf` - PDF processing
- `POST /api/chunk` - Text chunking
- `POST /api/stage1` - Stage 1 block discovery
- `POST /api/stage2` - Stage 2 value extraction
- `POST /api/reset` - Reset application state

---

#### 2. `pdf_processing/processor.py`
**Purpose**: PDF text and table extraction

**Key Function**: `process_pdf(pdf_path)`

**What It Does:**
1. **Dual-Method Text Extraction**:
   - Standard extraction using `pdfplumber.extract_text()`
   - Word-based extraction for headers/footers/page numbers
   - Uses whichever method captures more content

2. **Table Detection**:
   - Uses line-based strategy with custom settings
   - Detects vertical and horizontal lines
   - Finds table boundaries through line intersections

3. **Table Merging**:
   - Scans consecutive tables on same page
   - Merges tables with same column structure
   - Flattens fragmented tables into cohesive units

4. **Text Combination**:
   - Inserts page markers (`--- Page X ---`)
   - Inserts formatted tables at end of respective pages
   - Returns combined text with structure preserved

**Key Features:**
- Single-pass processing (opens PDF once)
- Handles empty pages and tables
- Preserves document structure
- Fallback to PyPDF2 if pdfplumber fails

---

#### 3. `chunking/chunker.py`
**Purpose**: Text chunking by articles using TOC parsing

**Key Function**: `chunk(text)`

**What It Does:**
1. **TOC Parsing**:
   - Finds Table of Contents section
   - Extracts articles with Roman numerals (I, II, III, etc.)
   - Identifies article titles and page numbers
   - Determines article boundaries

2. **Article Detection**:
   - Locates TOC end position in text
   - Searches for article headers directly in text
   - Handles variations (same line, separate lines, case variations)
   - Records text positions where articles start

3. **Chunk Classification**:
   - Classifies each chunk by article title
   - Maps to `chunkType` (definitions, credits, negative_covenants, etc.)
   - Handles cover page separately

4. **Chunk Creation**:
   - Creates Cover Page chunk (before first article)
   - Creates article chunks based on text positions
   - Maps text positions to PDF page numbers
   - Calculates chunk metadata (pages, character count)

**Key Features:**
- Text-based detection (no page number dependency)
- Handles missing articles gracefully
- Preserves article boundaries
- Works with various TOC formats
- Fallback chunking if TOC parsing fails

**Supported Chunk Types:**
- `cover` - Cover page
- `definitions` - Definitions article
- `representations` - Representations and Warranties
- `negative_covenants` - Negative Covenants
- `credits` - Credits/The Credits article
- `events_of_default` - Events of Default
- `other` - Unclassified articles

---

#### 4. `extraction/stage1_extractor.py`
**Purpose**: Stage 1 - Block discovery and isolation

**Key Function**: `extract(text_chunk, chunk_type, schema)`

**What It Does:**
1. **Schema Loading**:
   - Loads Stage 1 schema for the chunk type
   - Extracts block definitions (blockId, anchorPattern, valueType, label)

2. **Prompt Creation**:
   - Creates comprehensive prompt with:
     - System message (anti-hallucination)
     - Schema block definitions
     - Chunk text
     - Extraction instructions

3. **LLM Processing**:
   - Sends request to OpenAI GPT-4o-mini
   - Temperature: 0.1 (low for accuracy)
   - Parses response into blocks

4. **Block Parsing**:
   - Parses multiline BlockText (handles tables, spacing, multi-paragraph)
   - Extracts blockId, valueType, and full text
   - Handles "Not Found" blocks

**Key Features:**
- Multiline text preservation
- Handles different schema structures (targets, blocks, blockTemplates)
- Supports fieldId (cover) and blockId (others)
- Preserves original formatting

**Output Format:**
```json
{
  "blockId": "revolvingCreditCommitment",
  "valueType": "commitment",
  "text": "Full block text including tables..."
}
```

---

#### 5. `extraction/stage2_extractor.py`
**Purpose**: Stage 2 - Value extraction with confidence scoring

**Key Function**: `extract(block, chunk_type, schema)`

**What It Does:**
1. **Block Validation**:
   - Checks if block text exists and is not "Not Found"
   - Returns empty result if block is missing

2. **Schema Routing**:
   - Matches block's `valueType` to schema section
   - Loads field definitions for that valueType

3. **Prompt Creation**:
   - Creates prompt with:
     - System message
     - Field definitions with extraction hints
     - Block text only (not full chunk)
     - Output format instructions
     - Summarized output mode instructions (if applicable)

4. **LLM Processing**:
   - Sends request to OpenAI GPT-4o-mini
   - Temperature: 0.1
   - Parses response into field-value pairs

5. **Confidence Calculation**:
   - Calculates 7-factor confidence score
   - Type-aware validation
   - Anchor proximity scoring
   - Ambiguity detection
   - Faithfulness checks (for summarized outputs)

**Key Features:**
- Field type validation (text, quantitative_metric, date, location, duration, boolean)
- Format validation with regex patterns
- Evidence locality checks
- Anchor proximity scoring
- Multiple candidate detection
- Summarized output support
- Display percentage capped at 95%

**Confidence Factors:**
1. Value Presence (0-3)
2. Format Validity (0-2)
3. Evidence Support (0-2)
4. Completeness (0-1)
5. Anchor Proximity (0-1)
6. Ambiguity Penalty (-0.5 to 0)
7. Faithfulness (0-1, for summarized outputs)

**Output Format:**
```json
{
  "blockId": "revolvingCreditCommitment",
  "valueType": "commitment",
  "values": {
    "commitmentAmount": "USD 500,000,000.00"
  },
  "confidence": {
    "commitmentAmount": {
      "level": "High",
      "score": 8.5,
      "max_score": 9,
      "percentage": 94.4,
      "display_percentage": 94.4,
      "factors": [...],
      "isMissing": false,
      "ambiguousCandidates": false,
      "multipleMatches": 0,
      "anchorNotFound": false
    }
  }
}
```

---

#### 6. `schemas/schema_loader.py`
**Purpose**: Schema loading and mapping utilities

**Key Functions:**
- `load_stage1_schema(chunk_type)` - Load Stage 1 schema
- `load_stage2_schema(chunk_type)` - Load Stage 2 schema

**What It Does:**
- Maps chunk types to schema file names
- Loads JSON schema files
- Returns schema dictionaries
- Handles missing schemas gracefully

**Schema Mapping:**
- Stage 1: 6 chunk types → 6 schema files
- Stage 2: 4 chunk types → 4 schema files

---

### Frontend Components

#### 1. `frontend/index.html`
**Purpose**: Single-page application UI

**Key Features:**

**State Management:**
- JavaScript variables for application state
- Tracks uploaded file, processing results, chunks, Stage 1/2 results
- Manages UI state (expanded chunks, confidence details)

**User Interface Elements:**

1. **File Upload Section**:
   - File input for PDF upload
   - Upload status display
   - File metadata display

2. **Processing Results Section**:
   - Processing statistics (pages, tables, text length)
   - Full extracted text display (not truncated)
   - "Chunk Text" button

3. **Chunking Results Section**:
   - Chunk list with metadata
   - Expand/collapse for each chunk
   - Full chunk text display (not truncated)
   - "Run Stage 1" button

4. **Stage 1 Results Section**:
   - Block list for each chunk
   - Expandable block text view
   - Block metadata (blockId, valueType)
   - "Run Stage 2" button

5. **Stage 2 Results Section**:
   - Extracted values organized by block
   - Confidence levels with color coding
   - Expandable confidence details
   - Factor breakdowns

**API Integration:**
- Makes requests to `http://localhost:5001/api/*`
- Handles errors gracefully
- Shows loading states
- Automatic state reset on page load

---

## Data Flow

### Complete Request-Response Cycle

```
1. USER ACTION
   └─> User selects PDF file in browser

2. FRONTEND UPLOAD
   └─> FormData created with file
   └─> POST request to http://localhost:5001/api/upload
   └─> File uploaded and file_id returned
   └─> State reset (clears previous results)

3. USER INITIATES PROCESSING
   └─> User clicks "Process PDF" button
   └─> POST request to /api/process-pdf
   └─> Request body: { file_id }

4. BACKEND PDF PROCESSING
   └─> Flask receives file_id
   └─> File lookup by file_id
   └─> pdf_processing.process_pdf() called
   └─> PDF opened and processed:
       - Text extracted (dual-method)
       - Tables detected and merged
       - Combined text created
   └─> Processing results returned

5. USER INITIATES CHUNKING
   └─> User clicks "Chunk Text" button
   └─> POST request to /api/chunk
   └─> Request body: { text: full_extracted_text }

6. BACKEND CHUNKING
   └─> chunking.chunker.chunk() called
   └─> TOC parsed to identify articles
   └─> Article headers found in text
   └─> Chunks created with chunkType classification
   └─> Chunking results returned

7. USER INITIATES STAGE 1
   └─> User clicks "Run Stage 1" button
   └─> POST request to /api/stage1

8. BACKEND STAGE 1 EXTRACTION
   └─> For each chunk with schema:
       a. Schema selected based on chunkType
       b. stage1_extractor.extract() called
       c. Prompt created with schema and chunk text
       d. Request sent to OpenAI API
       e. Response parsed into blocks
   └─> Stage 1 results organized by chunk
   └─> Results returned

9. USER INITIATES STAGE 2
   └─> User clicks "Run Stage 2" button
   └─> POST request to /api/stage2

10. BACKEND STAGE 2 EXTRACTION
    └─> For each chunk with Stage 2 schema:
        a. Stage 2 schema loaded
        b. For each block from Stage 1:
            - Skip if block text is "Not Found" (optimization)
            - Match block's valueType to schema section
            - stage2_extractor.extract() called
            - Prompt created with field definitions and block text
            - Request sent to OpenAI API
            - Response parsed into field-value pairs
            - Confidence calculated (7 factors)
        c. Results organized by block
    └─> Stage 2 results returned

11. FRONTEND DISPLAY
    └─> Stage 2 results displayed
    └─> Values shown with confidence levels
    └─> Expandable confidence details
    └─> User can review all extractions
```

---

## Key Functionality

### 1. PDF Upload & Validation

**Location**: `app.py` (`/api/upload` route)

**Functionality:**
- Accepts only PDF files (enforced in backend)
- File validation (PDF extension check)
- Unique file ID generation (UUID)
- File storage in `uploads/` directory
- Automatic cleanup of old files

**Error Handling:**
- Backend returns 400 if file is not PDF
- Frontend displays error message

---

### 2. PDF Text and Table Extraction

**Location**: `pdf_processing/processor.py`

**Functionality:**
- Dual-method text extraction:
  - Standard extraction for main content
  - Word-based extraction for headers/footers/page numbers
- Table detection using line-based strategy
- Automatic table merging for fragmented tables
- Page marker insertion (`--- Page X ---`)
- Table formatting and insertion

**Key Features:**
- Single-pass processing (opens PDF once)
- Handles empty pages and tables
- Preserves document structure
- Fallback to PyPDF2 if pdfplumber fails

---

### 3. Intelligent Text Chunking

**Location**: `chunking/chunker.py`

**Core Strategy:**

1. **TOC Parsing**: 
   - Finds Table of Contents section
   - Extracts articles with Roman numerals
   - Identifies article titles and page numbers

2. **Text-Based Article Detection**:
   - Searches for article headers directly in text
   - No dependency on page number mapping
   - Handles variations in formatting

3. **Chunk Classification**:
   - Classifies chunks by article title
   - Maps to chunkType for schema routing

4. **Chunk Creation**:
   - Cover Page chunk (before first article)
   - Article chunks based on text positions
   - Page number mapping for metadata

**Advantages:**
- Robust (works with inconsistent page numbers)
- Accurate (direct text matching)
- Flexible (handles different TOC formats)
- Semantic classification enables proper schema routing

---

### 4. Stage 1 - Block Discovery

**Location**: `extraction/stage1_extractor.py`

**Core Strategy:**

1. **Schema-Based Block Identification**: 
   - Uses predefined Stage 1 JSON schemas
   - Each schema defines blocks to find (anchorPattern, label, valueType)
   - Extraction hints guide the AI

2. **Prompt Engineering**:
   - System message (anti-hallucination)
   - Full schema with block definitions
   - Chunk text (up to 150,000 characters)
   - Clear block extraction instructions

3. **Block Extraction**:
   - Locates blocks using anchor patterns and semantic equivalents
   - Extracts entire verbatim block text (multiline support)
   - Assigns valueType to each block
   - Returns "Not Found" for missing blocks

4. **Multiline Text Handling**:
   - Preserves tables, spacing, multi-paragraph content
   - Handles complex block structures

**Key Features:**
- Multiline text preservation
- Handles different schema structures
- Supports both fieldId and blockId
- Preserves original formatting

---

### 5. Stage 2 - Value Extraction with Confidence

**Location**: `extraction/stage2_extractor.py`

**Core Strategy:**

1. **Block Skipping Optimization**: 
   - Automatically skips blocks marked "Not Found" in Stage 1
   - Reduces LLM calls by ~42%
   - Returns empty result for skipped blocks

2. **Schema-Based Extraction**: 
   - Uses predefined Stage 2 JSON schemas
   - Routes by block's valueType
   - Each schema section defines fields to extract

3. **Prompt Engineering**:
   - System message (anti-hallucination)
   - Field definitions with extraction hints (pattern, notes, type)
   - Block text only (not full chunk)
   - Summarized output mode instructions (if applicable)

4. **Value Extraction**:
   - Extracts values from block text only
   - Handles nested field structures
   - Supports collectMultiple for list fields
   - Returns "Not Found" for missing values

5. **Confidence Calculation**:
   - 7-factor confidence model
   - Type-aware validation
   - Format validation with regex
   - Evidence locality checks
   - Anchor proximity scoring
   - Ambiguity detection
   - Faithfulness checks (for summarized outputs)

**Key Features:**
- Field type validation (6 types supported)
- Format validation with regex patterns
- Evidence locality (exact match for numbers, token matching for text)
- Anchor proximity (distance to schema pattern)
- Multiple candidate detection
- Summarized output support
- Display percentage capped at 95%

---

### 6. Confidence Scoring System

**Location**: `extraction/stage2_extractor.py` (`_calculate_confidence` method)

**7-Factor Model:**

1. **Value Presence** (0-3 points)
   - Found: 3 points
   - Not Found: 0 points (marked as "Not Present")

2. **Format Validity** (0-2 points)
   - Type-aware regex validation
   - Quantitative metrics: currency, percent, ratio, basis points, numbers
   - Dates: numeric and month-style
   - Locations: Section/Schedule/Exhibit references
   - Durations: time periods
   - Booleans: Yes/No/True/False/Automatic

3. **Evidence Support** (0-2 points)
   - Exact substring match for numeric values: 2 points
   - Meaningful token matching for text: 1-2 points
   - Anchor coverage for summarized outputs

4. **Completeness** (0-1 point)
   - List count sanity for multi-value fields
   - Format validity for single values

5. **Anchor Proximity** (0-1 point)
   - Distance from schema pattern anchor to extracted value
   - Within 100 chars: full score
   - Degrades linearly up to 500 chars

6. **Ambiguity Penalty** (-0.5 to 0)
   - Detects multiple candidates of same format class
   - Applies -0.5 penalty if ambiguous
   - Flags: `ambiguousCandidates`, `multipleMatches`

7. **Faithfulness** (0-1 point, summarized outputs only)
   - Checks if summary numbers appear in source
   - Requires key rate terms for rate definitions
   - Validates summary doesn't introduce new numbers

**Confidence Levels:**
- **High** (≥75%): Strong confidence across all factors
- **Medium** (50-74%): Moderate confidence with some uncertainty
- **Low** (<50%): Low confidence, requires review
- **Not Present** (0%): Value not found (includes `isMissing: true`)

**Display Percentage:**
- Internal percentage: Uncapped (0-100%)
- Display percentage: Capped at 95% to avoid false certainty
- Ambiguity flags shown in UI

---

### 7. Results Display

**Location**: `frontend/index.html`

**Features:**

- **Structured Display**: Results organized by chunk and block
- **Field-Value Pairs**: Clear display of extracted fields
- **Confidence Levels**: Color-coded confidence badges
- **Expandable Details**: Confidence factor breakdowns
- **Block Text View**: Full block text for verification
- **Navigation**: Step-by-step workflow with buttons

---

### 8. Error Handling

**Backend Error Handling:**
- File type validation
- File existence checks
- PDF parsing errors
- Missing environment variables
- LLM API failures
- TOC parsing failures
- Connection errors

**Frontend Error Handling:**
- Network errors
- API error responses
- User-friendly error messages
- Loading state management
- Graceful degradation

---

## Configuration Files

### 1. Schema Files

**Location**: `schema/` directory

**Stage 1 Schemas:**
- `cover.stage1.json` - Cover page blocks (uses `targets` structure)
- `definitions.stage1.json` - Definition blocks (uses `blocks` structure)
- `representations.stage1.json` - Representation blocks
- `negativeCovenants.stage1.json` - Covenant blocks (uses `blockTemplates` structure)
- `credits.stage1.json` - Credit facility blocks
- `eventsOfDefault.stage1.json` - Default event blocks

**Stage 2 Schemas:**
- `definitions.stage2.json` - Definition value extraction (uses `schemasByValueType`)
- `negativeCovenants.stage2.json` - Covenant value extraction
- `credits.stage2.json` - Credit facility value extraction
- `eventsOfDefault.stage2.json` - Default event value extraction

**Schema Structure:**
- Stage 1: Defines blocks to find (blockId, anchorPattern, valueType, label)
- Stage 2: Defines fields to extract (fieldName, extractionHint, type, collectMultiple, outputMode)

---

### 2. `requirements.txt`
**Purpose**: Python package dependencies

**Key Dependencies:**
- `Flask`: Web framework
- `flask-cors`: Cross-origin resource sharing
- `pdfplumber`: PDF text and table extraction
- `PyPDF2`: PDF fallback extraction
- `openai`: OpenAI API client
- `python-dotenv`: Environment variable loading

---

### 3. Environment Variables (`.env`)
**Purpose**: Application configuration

**Required Variables:**
- `OPENAI_API_KEY`: OpenAI API key (required)

**Optional Variables:**
- `OPENAI_MODEL`: Model to use (default: `gpt-4o-mini`)
- `FLASK_PORT`: Server port (default: `5001`)
- `UPLOAD_CLEANUP_AGE_HOURS`: Hours before cleaning up uploads (default: `24`)

**Location**: Project root (not committed to git)

---

## API Documentation

### Endpoints

#### `GET /`
**Purpose**: Serve frontend HTML

**Response:**
- Content-Type: `text/html`
- Body: Frontend HTML file

---

#### `GET /api/health`
**Purpose**: Health check endpoint

**Response:**
```json
{
  "status": "ok"
}
```

---

#### `POST /api/upload`
**Purpose**: Upload a credit agreement PDF file

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: `file` (PDF file)

**Success Response:**
```json
{
  "message": "File uploaded successfully",
  "file_id": "uuid-string",
  "filename": "document.pdf",
  "file_size": 2133718
}
```

**Error Responses:**
- `400 Bad Request`: No file provided, empty filename, or invalid file type
- `500 Internal Server Error`: File save error

---

#### `POST /api/process-pdf`
**Purpose**: Process an uploaded PDF file and extract text and tables

**Request:**
- Method: `POST`
- Content-Type: `application/json`
- Body:
```json
{
  "file_id": "uuid-string"
}
```

**Success Response:**
```json
{
  "status": "success",
  "file_id": "uuid-string",
  "page_count": 179,
  "table_count": 4,
  "text_length": 537373,
  "full_text": "Complete extracted text with tables..."
}
```

**Error Responses:**
- `400 Bad Request`: Missing file_id
- `404 Not Found`: File not found
- `500 Internal Server Error`: PDF processing error

---

#### `POST /api/chunk`
**Purpose**: Chunk the extracted text into articles based on Table of Contents

**Request:**
- Method: `POST`
- Content-Type: `application/json`
- Body:
```json
{
  "text": "Full extracted text from /api/process-pdf endpoint"
}
```

**Success Response:**
```json
{
  "status": "success",
  "chunks": [
    {
      "chunkId": "uuid",
      "chunkType": "definitions",
      "title": "ARTICLE I — DEFINITIONS",
      "text": "Full chunk text...",
      "metadata": {
        "charCount": 143912,
        "startPage": 7,
        "endPage": 48
      }
    }
  ]
}
```

**Error Responses:**
- `400 Bad Request`: Missing text
- `500 Internal Server Error`: Chunking error (e.g., TOC parsing failure)

---

#### `POST /api/stage1`
**Purpose**: Stage 1 extraction - Block discovery

**Request:**
- Method: `POST`
- No body required (uses chunks from previous step)

**Success Response:**
```json
{
  "status": "success",
  "results": {
    "chunk-id": {
      "chunkId": "uuid",
      "chunkType": "definitions",
      "blocks": [
        {
          "blockId": "revolvingCreditCommitment",
          "valueType": "commitment",
          "text": "Full block text..."
        }
      ]
    }
  }
}
```

**Error Responses:**
- `400 Bad Request`: Document not chunked yet
- `500 Internal Server Error`: Extraction error

---

#### `POST /api/stage2`
**Purpose**: Stage 2 extraction - Value extraction with confidence

**Request:**
- Method: `POST`
- No body required (uses Stage 1 results)

**Success Response:**
```json
{
  "status": "success",
  "results": {
    "chunk-id": {
      "chunkId": "uuid",
      "chunkType": "definitions",
      "extractions": [
        {
          "blockId": "revolvingCreditCommitment",
          "valueType": "commitment",
          "values": {
            "commitmentAmount": "USD 500,000,000.00"
          },
          "confidence": {
            "commitmentAmount": {
              "level": "High",
              "score": 8.5,
              "max_score": 9,
              "percentage": 94.4,
              "display_percentage": 94.4,
              "factors": [...],
              "isMissing": false,
              "ambiguousCandidates": false,
              "multipleMatches": 0,
              "anchorNotFound": false
            }
          }
        }
      ]
    }
  }
}
```

**Error Responses:**
- `400 Bad Request`: Stage 1 not run yet
- `500 Internal Server Error`: Extraction error

---

#### `POST /api/reset`
**Purpose**: Reset application state and clean up old uploads

**Request:**
- Method: `POST`
- No body required

**Success Response:**
```json
{
  "status": "success",
  "message": "State reset and old uploads cleaned up"
}
```

---

## Frontend Documentation

### Component Structure

```
index.html (single-page application)
├── File Upload Section
│   ├── File Input
│   └── Upload Status
├── Processing Results Section
│   ├── Statistics Display
│   ├── Extracted Text Display (full text, not truncated)
│   └── Chunk Text Button
├── Chunking Results Section
│   ├── Chunks Summary
│   ├── Chunks List
│   │   └── Chunk Cards (expandable, full text)
│   └── Run Stage 1 Button
├── Stage 1 Results Section
│   ├── Blocks Summary
│   ├── Blocks List
│   │   └── Block Cards (expandable, full block text)
│   └── Run Stage 2 Button
└── Stage 2 Results Section
    ├── Extractions Summary
    ├── Extractions List
    │   └── Extraction Cards
    │       ├── Field-Value Pairs
    │       ├── Confidence Badges
    │       └── Expandable Confidence Details
    └── Factor Breakdowns
```

### State Management

**JavaScript Variables:**
- `currentState`: Tracks application state (uploaded, processed, chunked, stage1Complete, stage2Complete)
- `API_BASE`: API base URL (http://localhost:5001)

**No External State Management:**
- Simple variable-based state is sufficient for this use case
- State resets on page load

### Styling Approach

- **Inline Styles**: Component-specific inline styles
- **CSS Classes**: Reusable classes for common patterns
- **Responsive Design**: CSS Grid and Flexbox for layouts
- **Modern UI**: Card-based design with shadows and borders
- **Color Coding**: Confidence levels have color-coded badges

### User Workflow

1. **Upload**: User selects and uploads PDF file
2. **Process**: User clicks "Process PDF" button
3. **View Results**: User sees processing statistics and extracted text (full text)
4. **Chunk**: User clicks "Chunk Text" button
5. **View Chunks**: User sees chunks list with expand/collapse options (full text)
6. **Stage 1**: User clicks "Run Stage 1" button
7. **View Blocks**: User sees blocks list with expandable block text (full text)
8. **Stage 2**: User clicks "Run Stage 2" button
9. **View Extraction**: User sees structured extraction results with confidence
10. **Review Confidence**: User can expand confidence details to see factor breakdowns
11. **Navigate**: User can reset and start new analysis

---

## Summary

CreditSeer automates the extraction of structured data from credit agreement PDFs using a two-stage, schema-driven LLM architecture. The backend processes PDFs through text extraction, intelligent chunking, Stage 1 block discovery, and Stage 2 value extraction with confidence scoring. The frontend provides an intuitive step-by-step interface for uploading documents and viewing results organized by chunk and block with detailed confidence metadata.

**Key Strengths:**
- Two-stage extraction minimizes hallucination and cross-term contamination
- Comprehensive PDF processing (text + tables)
- Intelligent article-based chunking
- Schema-driven extraction with anti-hallucination measures
- Multi-factor confidence calculation with detailed breakdowns
- Block skipping optimization reduces LLM calls by ~42%
- Step-driven workflow ensures accuracy and transparency
- Modern, responsive UI
- Robust error handling
- Full text display (no truncation)

**Areas for Enhancement:**
- Batch processing (multiple PDFs)
- Export to Excel/CSV/JSON
- Custom schemas
- Historical comparison
- User authentication
- Database storage
- Parallel chunk/block processing
- Progress indicators
- Result validation and verification

---

*Last Updated: December 2024*
