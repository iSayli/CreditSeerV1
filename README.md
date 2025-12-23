# CreditSeer - Credit Agreement Analysis System

CreditSeer is a step-driven application that ingests credit agreement PDFs and extracts structured legal and financial terms using a two-stage, schema-driven LLM architecture.

## Features

- **Step-by-step workflow**: Each stage runs only when the user clicks a button
- **Transparent output**: View results at every stage before proceeding
- **Two-stage extraction**: 
  - Stage 1: Block-level text extraction with valueType assignment
  - Stage 2: Structured value extraction with confidence metadata
- **Schema-driven**: Extraction follows predefined schemas based on chunk type
- **Trustworthy**: Designed for credit analysts with full visibility into the process

## Setup

### Prerequisites

- Python 3.8+
- OpenAI API key

### Installation

1. Clone the repository:
```bash
cd CreditSeerV1
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root:
```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
MAX_CHUNK_CHAR_LIMIT=150000
```

4. Create the uploads directory:
```bash
mkdir uploads
```

## Running the Application

1. Start the Flask backend:
```bash
python app.py
```

The backend will run on `http://localhost:5001` (defaults to 5001 as port 5000 is often used by AirPlay on macOS)

2. Open the frontend:
Open `frontend/index.html` in your web browser, or serve it using a simple HTTP server:
```bash
cd frontend
python -m http.server 8000
```

Then navigate to `http://localhost:8000`

## Usage

1. **Upload PDF**: Click "Choose PDF File" and select a credit agreement PDF
2. **Process PDF**: Click "Process PDF" to extract text from the document
3. **Chunk Text**: Click "Chunk Text" to split the document into semantic articles
4. **Run Stage 1**: Click "Run Stage 1" to extract block-level text with valueTypes
5. **Run Stage 2**: Click "Run Stage 2" to extract structured values with confidence levels

## Architecture

### Backend Structure

```
CreditSeerV1/
├── app.py                 # Flask application and routes
├── pdf_processing/        # PDF text extraction
├── chunking/              # Document chunking into articles
├── extraction/            # Stage 1 and Stage 2 extractors
├── schemas/               # Schema loading and mapping
└── schema/                # JSON schema definitions
```

### Schema Mapping

- **cover**: `cover.stage1.json`
- **definitions**: `definitions.stage1.json` → `definitions.stage2.json`
- **representations**: `representations.stage1.json`
- **negative_covenants**: `negativeCovenants.stage1.json` → `negativeCovenants.stage2.json`

### Extraction Flow

1. PDF is uploaded and processed to extract text
2. Text is chunked into semantic articles (definitions, covenants, etc.)
3. Chunks are classified and mapped to appropriate schemas
4. **Stage 1**: Extract verbatim block text with valueType assignment
5. **Stage 2**: Extract structured values from Stage 1 blocks, with confidence metadata

## API Endpoints

- `POST /api/upload` - Upload PDF file
- `POST /api/process-pdf` - Process PDF to extract text
- `POST /api/chunk` - Chunk document into articles
- `POST /api/stage1` - Run Stage 1 extraction
- `POST /api/stage2` - Run Stage 2 extraction
- `GET /api/health` - Health check

## Design Principles

- Show every intermediate output
- Never hallucinate
- Isolate text before extracting values
- Surface uncertainty explicitly
- Optimize for analyst trust

## Notes

- The application uses in-memory state (not suitable for production)
- For production use, implement proper database storage
- Ensure OpenAI API key is properly secured
- PDF processing supports both pdfplumber and PyPDF2 as fallback

