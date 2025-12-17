import os
import time
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import uuid
import json

from pdf_processing.processor import PDFProcessor
from chunking.chunker import DocumentChunker
from extraction.stage1_extractor import Stage1Extractor
from extraction.stage2_extractor import Stage2Extractor
from schemas.schema_loader import SchemaLoader

load_dotenv()

app = Flask(__name__, static_folder='frontend')
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
UPLOAD_CLEANUP_AGE_HOURS = 1  # Clean up files older than 1 hour

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def cleanup_old_uploads():
    """Remove uploaded files older than UPLOAD_CLEANUP_AGE_HOURS"""
    try:
        current_time = time.time()
        cutoff_time = current_time - (UPLOAD_CLEANUP_AGE_HOURS * 3600)
        deleted_count = 0
        
        if not os.path.exists(UPLOAD_FOLDER):
            return deleted_count
        
        for filename in os.listdir(UPLOAD_FOLDER):
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            try:
                # Check if it's a file and get modification time
                if os.path.isfile(filepath):
                    file_mtime = os.path.getmtime(filepath)
                    if file_mtime < cutoff_time:
                        os.remove(filepath)
                        deleted_count += 1
            except Exception as e:
                # Skip files that can't be deleted
                continue
        
        return deleted_count
    except Exception as e:
        # Don't fail if cleanup fails
        return 0

# Global state (in production, use a proper database)
app_state = {
    'uploaded_file': None,
    'extracted_text': None,
    'chunks': None,
    'stage1_results': {},
    'stage2_results': {}
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Serve frontend"""
    return send_from_directory('frontend', 'index.html')

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

@app.route('/api/reset', methods=['POST'])
def reset_state():
    """Reset application state and clean up uploads"""
    # Delete current uploaded file if exists
    if app_state['uploaded_file'] and os.path.exists(app_state['uploaded_file']['filepath']):
        try:
            os.remove(app_state['uploaded_file']['filepath'])
        except:
            pass
    
    # Clean up all old uploads
    deleted_count = cleanup_old_uploads()
    
    # Reset state
    app_state['uploaded_file'] = None
    app_state['extracted_text'] = None
    app_state['chunks'] = None
    app_state['stage1_results'] = {}
    app_state['stage2_results'] = {}
    
    return jsonify({
        'status': 'success',
        'message': 'State reset successfully',
        'cleanup': f'Cleaned up {deleted_count} file(s)'
    })

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload PDF file"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Only PDF files are allowed.'}), 400
    
    # Clean up old uploads before saving new one
    deleted_count = cleanup_old_uploads()
    
    # Delete previous uploaded file if exists
    if app_state['uploaded_file'] and os.path.exists(app_state['uploaded_file']['filepath']):
        try:
            os.remove(app_state['uploaded_file']['filepath'])
        except:
            pass  # Ignore errors when deleting old file
    
    # Save file
    filename = f"{uuid.uuid4()}_{file.filename}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    # Get file info
    file_size = os.path.getsize(filepath)
    
    app_state['uploaded_file'] = {
        'filename': file.filename,
        'filepath': filepath,
        'size': file_size
    }
    
    # Reset downstream state
    app_state['extracted_text'] = None
    app_state['chunks'] = None
    app_state['stage1_results'] = {}
    app_state['stage2_results'] = {}
    
    return jsonify({
        'status': 'success',
        'filename': file.filename,
        'size': file_size,
        'message': 'File uploaded successfully',
        'cleanup': f'Cleaned up {deleted_count} old file(s)'
    })

@app.route('/api/process-pdf', methods=['POST'])
def process_pdf():
    """Process PDF to extract text"""
    if not app_state['uploaded_file']:
        return jsonify({'error': 'No file uploaded'}), 400
    
    try:
        processor = PDFProcessor()
        result = processor.process(app_state['uploaded_file']['filepath'])
        
        app_state['extracted_text'] = result
        
        return jsonify({
            'status': 'success',
            'text': result['text'],
            'metadata': result['metadata']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chunk', methods=['POST'])
def chunk_document():
    """Chunk document into articles"""
    if not app_state['extracted_text']:
        return jsonify({'error': 'PDF not processed yet'}), 400
    
    try:
        chunker = DocumentChunker()
        chunks = chunker.chunk(app_state['extracted_text']['text'])
        
        app_state['chunks'] = chunks
        
        return jsonify({
            'status': 'success',
            'chunks': chunks
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stage1', methods=['POST'])
def run_stage1():
    """Run Stage 1 extraction on all chunks"""
    if not app_state['chunks']:
        return jsonify({'error': 'Document not chunked yet'}), 400
    
    try:
        extractor = Stage1Extractor()
        schema_loader = SchemaLoader()
        
        stage1_results = {}
        
        for chunk in app_state['chunks']:
            chunk_type = chunk['chunkType']
            
            # Skip chunks without schemas
            if chunk_type == 'other':
                continue
            
            # Load appropriate schema
            schema = schema_loader.load_stage1_schema(chunk_type)
            if not schema:
                continue
            
            # Run extraction
            result = extractor.extract(chunk['text'], chunk_type, schema)
            stage1_results[chunk['chunkId']] = {
                'chunkId': chunk['chunkId'],
                'chunkType': chunk_type,
                'blocks': result
            }
        
        app_state['stage1_results'] = stage1_results
        
        return jsonify({
            'status': 'success',
            'results': stage1_results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stage2', methods=['POST'])
def run_stage2():
    """Run Stage 2 extraction on Stage 1 blocks"""
    if not app_state['stage1_results']:
        return jsonify({'error': 'Stage 1 not run yet'}), 400
    
    try:
        extractor = Stage2Extractor()
        schema_loader = SchemaLoader()
        
        stage2_results = {}
        
        for chunk_id, stage1_data in app_state['stage1_results'].items():
            chunk_type = stage1_data['chunkType']
            blocks = stage1_data['blocks']
            
            # Skip Stage 2 for cover pages - Stage 1 already returned normalized values
            if chunk_type == 'cover':
                # Map Stage 1 "BlockText" to Stage 2 "values" for UI consistency
                cover_extractions = []
                for block in blocks:
                    block_id = block.get('blockId', 'Unknown')
                    text = block.get('text', '')
                    
                    if text and text != 'Not Found':
                        cover_extractions.append({
                            'blockId': block_id,
                            'valueType': block.get('valueType', ''),
                            'values': {block_id: text},
                            'confidence': {block_id: {'level': 'High', 'score': 1.0, 'percentage': 100.0, 'factors': [{'factor': 'Stage 1 Direct', 'status': 'Normalized from cover', 'score': 1, 'max': 1}]}},
                            'isCover': True
                        })
                
                stage2_results[chunk_id] = {
                    'chunkId': chunk_id,
                    'chunkType': chunk_type,
                    'extractions': cover_extractions
                }
                continue

            # Load Stage 2 schema if available
            schema = schema_loader.load_stage2_schema(chunk_type)
            if not schema:
                continue
            
            # Run extraction on each block (skip blocks that were not found in Stage 1)
            block_results = []
            for block in blocks:
                block_text = block.get('text', '')
                block_id = block.get('blockId', 'Unknown')
                
                # Skip Stage 2 if block was not found in Stage 1
                if not block_text or block_text == 'Not Found':
                    # Return empty result without making LLM call
                    block_results.append({
                        'blockId': block_id,
                        'valueType': block.get('valueType', ''),
                        'values': {},
                        'confidence': {},
                        'skipped': True,
                        'reason': 'Block not found in Stage 1'
                    })
                    continue
                
                # Only make LLM call for blocks that were found
                result = extractor.extract(block, chunk_type, schema)
                block_results.append(result)
            
            stage2_results[chunk_id] = {
                'chunkId': chunk_id,
                'chunkType': chunk_type,
                'extractions': block_results
            }
        
        app_state['stage2_results'] = stage2_results
        
        return jsonify({
            'status': 'success',
            'results': stage2_results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Validate environment
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("WARNING: OPENAI_API_KEY not found in environment variables")
    
    # Clean up old uploads on startup
    deleted_count = cleanup_old_uploads()
    if deleted_count > 0:
        print(f"Cleaned up {deleted_count} old uploaded file(s) on startup")
    
    port = int(os.getenv('FLASK_PORT', 5001))
    print(f"\n{'='*60}")
    print(f"CreditSeer is starting on http://localhost:{port}")
    print(f"{'='*60}\n")
    app.run(debug=True, port=port, host='0.0.0.0')

