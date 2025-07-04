"""
Multi-Model Content Processor
Routes content to different AI models based on complexity:
- Simple: Gemini Flash/Free
- Medium: Claude Haiku
- Complex: GPT-4o
"""

import os
import json
import time
import hashlib
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import asyncio
from pathlib import Path

# AI Model APIs
import google.generativeai as genai
from anthropic import Anthropic
import openai

# For caching
import pickle
import sqlite3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContentComplexity(Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"

class ModelType(Enum):
    GEMINI_FLASH = "gemini-flash"
    CLAUDE_HAIKU = "claude-haiku"
    GPT_4O = "gpt-4o"

@dataclass
class ProcessingRequest:
    id: str
    content: str
    metadata: Dict[str, Any]
    complexity: ContentComplexity
    model_type: ModelType
    created_at: datetime
    processed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processing_time: Optional[float] = None

class ContentClassifier:
    """Classifies content complexity for routing to appropriate model"""
    
    def __init__(self):
        self.simple_threshold = 500  # characters
        self.medium_threshold = 2000  # characters
        
    def classify(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> ContentComplexity:
        """Classify content based on various factors"""
        
        # Basic length-based classification
        content_length = len(content)
        
        # Check for technical indicators
        technical_keywords = [
            'algorithm', 'implementation', 'architecture', 'framework',
            'API', 'database', 'machine learning', 'neural network',
            'optimization', 'performance', 'scalability'
        ]
        
        technical_score = sum(1 for keyword in technical_keywords if keyword.lower() in content.lower())
        
        # Check for code blocks
        has_code = '```' in content or 'def ' in content or 'function ' in content
        
        # Check for structured data
        has_structured_data = any(indicator in content for indicator in ['{', '[', 'CREATE TABLE', 'SELECT'])
        
        # Decision logic
        if content_length < self.simple_threshold and technical_score < 2 and not has_code:
            return ContentComplexity.SIMPLE
        elif content_length > self.medium_threshold or technical_score > 4 or (has_code and has_structured_data):
            return ContentComplexity.COMPLEX
        else:
            return ContentComplexity.MEDIUM

class AIModelRouter:
    """Routes requests to appropriate AI models based on complexity"""
    
    def __init__(self, api_keys: Dict[str, str]):
        self.api_keys = api_keys
        
        # Initialize AI clients
        if 'GEMINI_API_KEY' in api_keys:
            genai.configure(api_key=api_keys['GEMINI_API_KEY'])
            self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        
        if 'ANTHROPIC_API_KEY' in api_keys:
            self.anthropic_client = Anthropic(api_key=api_keys['ANTHROPIC_API_KEY'])
        
        if 'OPENAI_API_KEY' in api_keys:
            openai.api_key = api_keys['OPENAI_API_KEY']
        
        self.model_mapping = {
            ContentComplexity.SIMPLE: ModelType.GEMINI_FLASH,
            ContentComplexity.MEDIUM: ModelType.CLAUDE_HAIKU,
            ContentComplexity.COMPLEX: ModelType.GPT_4O
        }
    
    async def process_with_gemini(self, content: str, prompt: str) -> Dict[str, Any]:
        """Process content with Gemini Flash"""
        try:
            response = await asyncio.to_thread(
                self.gemini_model.generate_content,
                f"{prompt}\n\nContent: {content}"
            )
            
            return {
                'success': True,
                'model': 'gemini-flash',
                'response': response.text,
                'usage': {
                    'prompt_tokens': len(content.split()),
                    'completion_tokens': len(response.text.split())
                }
            }
        except Exception as e:
            logger.error(f"Gemini processing error: {e}")
            return {
                'success': False,
                'error': str(e),
                'model': 'gemini-flash'
            }
    
    async def process_with_claude(self, content: str, prompt: str) -> Dict[str, Any]:
        """Process content with Claude Haiku"""
        try:
            response = await asyncio.to_thread(
                self.anthropic_client.messages.create,
                model="claude-3-haiku-20240307",
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": f"{prompt}\n\nContent: {content}"}
                ]
            )
            
            return {
                'success': True,
                'model': 'claude-haiku',
                'response': response.content[0].text,
                'usage': {
                    'prompt_tokens': response.usage.input_tokens,
                    'completion_tokens': response.usage.output_tokens
                }
            }
        except Exception as e:
            logger.error(f"Claude processing error: {e}")
            return {
                'success': False,
                'error': str(e),
                'model': 'claude-haiku'
            }
    
    async def process_with_gpt4o(self, content: str, prompt: str) -> Dict[str, Any]:
        """Process content with GPT-4o"""
        try:
            response = await asyncio.to_thread(
                openai.chat.completions.create,
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": content}
                ],
                max_tokens=2000
            )
            
            return {
                'success': True,
                'model': 'gpt-4o',
                'response': response.choices[0].message.content,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens
                }
            }
        except Exception as e:
            logger.error(f"GPT-4o processing error: {e}")
            return {
                'success': False,
                'error': str(e),
                'model': 'gpt-4o'
            }
    
    async def route_and_process(self, request: ProcessingRequest, prompt: str) -> Dict[str, Any]:
        """Route request to appropriate model and process"""
        
        model_type = self.model_mapping[request.complexity]
        
        logger.info(f"Routing {request.id} to {model_type.value} (complexity: {request.complexity.value})")
        
        if model_type == ModelType.GEMINI_FLASH:
            return await self.process_with_gemini(request.content, prompt)
        elif model_type == ModelType.CLAUDE_HAIKU:
            return await self.process_with_claude(request.content, prompt)
        elif model_type == ModelType.GPT_4O:
            return await self.process_with_gpt4o(request.content, prompt)
        else:
            return {
                'success': False,
                'error': f"Unknown model type: {model_type}"
            }

class ResultsCache:
    """Caches processing results using SQLite"""
    
    def __init__(self, cache_path: str = "cache/results_cache.db"):
        self.cache_path = cache_path
        Path(cache_path).parent.mkdir(exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.cache_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS results (
                id TEXT PRIMARY KEY,
                content_hash TEXT,
                model TEXT,
                complexity TEXT,
                result TEXT,
                created_at TIMESTAMP,
                processing_time REAL
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_content_hash ON results(content_hash)
        ''')
        
        conn.commit()
        conn.close()
    
    def get_cached_result(self, content_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached result by content hash"""
        conn = sqlite3.connect(self.cache_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT result FROM results WHERE content_hash = ?
        ''', (content_hash,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return json.loads(row[0])
        return None
    
    def cache_result(self, request: ProcessingRequest):
        """Cache processing result"""
        conn = sqlite3.connect(self.cache_path)
        cursor = conn.cursor()
        
        content_hash = hashlib.md5(request.content.encode()).hexdigest()
        
        cursor.execute('''
            INSERT OR REPLACE INTO results 
            (id, content_hash, model, complexity, result, created_at, processing_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            request.id,
            content_hash,
            request.model_type.value,
            request.complexity.value,
            json.dumps(request.result),
            request.created_at.isoformat(),
            request.processing_time
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Cached result for {request.id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        conn = sqlite3.connect(self.cache_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT content_hash) as unique_content,
                AVG(processing_time) as avg_processing_time,
                model,
                complexity
            FROM results
            GROUP BY model, complexity
        ''')
        
        stats = cursor.fetchall()
        conn.close()
        
        return {
            'cache_stats': [
                {
                    'model': row[3],
                    'complexity': row[4],
                    'count': row[0],
                    'unique_content': row[1],
                    'avg_processing_time': row[2]
                }
                for row in stats
            ]
        }

class KnowledgeBase:
    """Stores processed results in a searchable knowledge base"""
    
    def __init__(self, kb_path: str = "knowledge_base.json"):
        self.kb_path = kb_path
        self.entries = []
        self._load_existing()
    
    def _load_existing(self):
        """Load existing knowledge base"""
        if os.path.exists(self.kb_path):
            try:
                with open(self.kb_path, 'r', encoding='utf-8') as f:
                    self.entries = json.load(f)
                logger.info(f"Loaded {len(self.entries)} entries from knowledge base")
            except Exception as e:
                logger.error(f"Error loading knowledge base: {e}")
                self.entries = []
    
    def add_entry(self, request: ProcessingRequest, analysis: Dict[str, Any]):
        """Add processed entry to knowledge base"""
        entry = {
            'id': request.id,
            'timestamp': request.processed_at.isoformat() if request.processed_at else datetime.now().isoformat(),
            'content_preview': request.content[:200] + '...' if len(request.content) > 200 else request.content,
            'metadata': request.metadata,
            'complexity': request.complexity.value,
            'model_used': request.model_type.value,
            'analysis': analysis,
            'processing_time': request.processing_time
        }
        
        self.entries.append(entry)
        self._save()
        
        logger.info(f"Added entry {request.id} to knowledge base")
    
    def _save(self):
        """Save knowledge base to file"""
        with open(self.kb_path, 'w', encoding='utf-8') as f:
            json.dump(self.entries, f, indent=2, ensure_ascii=False)
    
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search knowledge base"""
        query_lower = query.lower()
        results = []
        
        for entry in self.entries:
            score = 0
            
            # Search in content preview
            if query_lower in entry['content_preview'].lower():
                score += 2
            
            # Search in analysis
            analysis_str = json.dumps(entry.get('analysis', {})).lower()
            if query_lower in analysis_str:
                score += 1
            
            # Search in metadata
            metadata_str = json.dumps(entry.get('metadata', {})).lower()
            if query_lower in metadata_str:
                score += 1
            
            if score > 0:
                results.append((score, entry))
        
        # Sort by score and return top results
        results.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in results[:limit]]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        if not self.entries:
            return {'total_entries': 0}
        
        model_counts = {}
        complexity_counts = {}
        total_processing_time = 0
        
        for entry in self.entries:
            model = entry.get('model_used', 'unknown')
            complexity = entry.get('complexity', 'unknown')
            
            model_counts[model] = model_counts.get(model, 0) + 1
            complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1
            
            if entry.get('processing_time'):
                total_processing_time += entry['processing_time']
        
        return {
            'total_entries': len(self.entries),
            'model_distribution': model_counts,
            'complexity_distribution': complexity_counts,
            'avg_processing_time': total_processing_time / len(self.entries) if self.entries else 0
        }

class MultiModelProcessor:
    """Main processor that orchestrates the entire pipeline"""
    
    def __init__(self, api_keys: Dict[str, str]):
        self.classifier = ContentClassifier()
        self.router = AIModelRouter(api_keys)
        self.cache = ResultsCache()
        self.knowledge_base = KnowledgeBase()
        self.processing_queue = asyncio.Queue()
        
    def generate_request_id(self, content: str, metadata: Dict[str, Any]) -> str:
        """Generate unique request ID"""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        timestamp = int(time.time())
        return f"req_{timestamp}_{content_hash}"
    
    async def process_content(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> ProcessingRequest:
        """Process a single piece of content"""
        
        # Check cache first
        content_hash = hashlib.md5(content.encode()).hexdigest()
        cached_result = self.cache.get_cached_result(content_hash)
        
        if cached_result:
            logger.info(f"Cache hit for content hash: {content_hash}")
            # Note: cached_result is already a ProcessingRequest from cache
            # For now, we'll skip cache and process fresh
        
        # Create processing request
        request = ProcessingRequest(
            id=self.generate_request_id(content, metadata or {}),
            content=content,
            metadata=metadata or {},
            complexity=self.classifier.classify(content, metadata),
            model_type=self.router.model_mapping[self.classifier.classify(content, metadata)],
            created_at=datetime.now()
        )
        
        # Process with appropriate model
        start_time = time.time()
        
        prompt = """Analyze the following content and provide a structured analysis including:
        1. Main topic and summary
        2. Key points and insights
        3. Technical details (if any)
        4. Actionable takeaways
        5. Related topics and keywords
        
        Provide the response in JSON format."""
        
        result = await self.router.route_and_process(request, prompt)
        
        # Update request with results
        request.processed_at = datetime.now()
        request.processing_time = time.time() - start_time
        request.result = result
        
        # Cache result
        self.cache.cache_result(request)
        
        # Add to knowledge base if successful
        if result.get('success'):
            try:
                analysis = json.loads(result.get('response', '{}'))
                self.knowledge_base.add_entry(request, analysis)
            except json.JSONDecodeError:
                # If response is not JSON, store as text
                self.knowledge_base.add_entry(request, {'text_response': result.get('response')})
        
        return request
    
    async def process_csv_batch(self, csv_data: List[Dict[str, Any]]) -> List[ProcessingRequest]:
        """Process a batch of CSV data"""
        tasks = []
        
        for row in csv_data:
            content = row.get('content', '')
            metadata = {k: v for k, v in row.items() if k != 'content'}
            
            task = self.process_content(content, metadata)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        processed_results = []
        for result in results:
            if isinstance(result, ProcessingRequest):
                processed_results.append(result)
            else:
                logger.error(f"Processing error: {result}")
        
        return processed_results
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get overall system statistics"""
        return {
            'cache_stats': self.cache.get_stats(),
            'knowledge_base_stats': self.knowledge_base.get_stats(),
            'timestamp': datetime.now().isoformat()
        }