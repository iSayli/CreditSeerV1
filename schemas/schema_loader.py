import json
import os
from typing import Dict, Optional

class SchemaLoader:
    """Load and manage extraction schemas"""
    
    SCHEMA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'schema')
    
    # Schema mapping
    STAGE1_MAPPING = {
        'cover': 'cover.stage1.json',
        'definitions': 'definitions.stage1.json',
        'representations': 'representations.stage1.json',
        'negative_covenants': 'negativeCovenants.stage1.json',
        'credits': 'credits.stage1.json',
        'events_of_default': 'eventsOfDefault.stage1.json',
    }
    
    STAGE2_MAPPING = {
        'definitions': 'definitions.stage2.json',
        'negative_covenants': 'negativeCovenants.stage2.json',
        'credits': 'credits.stage2.json',
        'events_of_default': 'eventsOfDefault.stage2.json',
    }
    
    def load_stage1_schema(self, chunk_type: str) -> Optional[Dict]:
        """Load Stage 1 schema for given chunk type"""
        if chunk_type not in self.STAGE1_MAPPING:
            return None
        
        filename = self.STAGE1_MAPPING[chunk_type]
        filepath = os.path.join(self.SCHEMA_DIR, filename)
        
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def load_stage2_schema(self, chunk_type: str) -> Optional[Dict]:
        """Load Stage 2 schema for given chunk type"""
        if chunk_type not in self.STAGE2_MAPPING:
            return None
        
        filename = self.STAGE2_MAPPING[chunk_type]
        filepath = os.path.join(self.SCHEMA_DIR, filename)
        
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, 'r') as f:
            return json.load(f)

