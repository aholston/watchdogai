"""Log embedding and vector storage for WatchDogAI"""

import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

import chromadb
from chromadb.config import Settings
from langchain_openai import OpenAIEmbeddings
from langchain_anthropic import ChatAnthropic

from .config import get_config


class LogEntry:
    """Represents a single log entry"""
    
    def __init__(self, raw_log: str, timestamp: Optional[datetime] = None, 
                 source: str = "unknown", metadata: Optional[Dict] = None):
        self.id = str(uuid.uuid4())
        self.raw_log = raw_log.strip()
        self.timestamp = timestamp or datetime.now()
        self.source = source
        self.metadata = metadata or {}
        
        # Parse structured content if possible
        self.structured_data = self._parse_structured_content()
        
        # Create searchable text
        self.searchable_text = self._create_searchable_text()
    
    def _parse_structured_content(self) -> Optional[Dict]:
        """Try to parse JSON or extract key-value pairs from log"""
        try:
            # Try JSON first
            if self.raw_log.strip().startswith('{'):
                return json.loads(self.raw_log)
        except json.JSONDecodeError:
            pass
        
        # Try to extract common syslog patterns
        # Format: timestamp hostname service[pid]: message
        import re
        syslog_pattern = r'(\w+\s+\d+\s+\d+:\d+:\d+)\s+(\w+)\s+([^:]+):\s*(.*)'
        match = re.match(syslog_pattern, self.raw_log)
        
        if match:
            return {
                'timestamp': match.group(1),
                'hostname': match.group(2),
                'service': match.group(3),
                'message': match.group(4)
            }
        
        return None
    
    def _create_searchable_text(self) -> str:
        """Create text optimized for semantic search"""
        parts = [self.raw_log]
        
        # Add structured data if available
        if self.structured_data:
            if isinstance(self.structured_data, dict):
                # Add key-value pairs
                for key, value in self.structured_data.items():
                    if isinstance(value, (str, int, float)):
                        parts.append(f"{key}: {value}")
        
        # Add metadata
        parts.append(f"source: {self.source}")
        
        return " | ".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'id': self.id,
            'raw_log': self.raw_log,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'searchable_text': self.searchable_text
        }
    
    def to_chroma_metadata(self) -> Dict[str, Any]:
        """Convert to ChromaDB-compatible metadata (flat structure)"""
        metadata = {
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
        }
        
        # Add structured data as flattened key-value pairs
        if self.structured_data:
            for key, value in self.structured_data.items():
                # Only add simple types that ChromaDB accepts
                if isinstance(value, (str, int, float, bool)) and value is not None:
                    metadata[f"struct_{key}"] = value
                elif isinstance(value, str):
                    metadata[f"struct_{key}"] = value[:100]  # Truncate long strings
        
        # Add custom metadata with prefix
        for key, value in self.metadata.items():
            if isinstance(value, (str, int, float, bool)) and value is not None:
                metadata[f"meta_{key}"] = value
        
        return metadata


class LogEmbeddings:
    """Handles log embedding and vector storage"""
    
    def __init__(self):
        self.config = get_config()
        self.embeddings = None
        self.chroma_client = None
        self.collection = None
        
        self._initialize_embeddings()
        self._initialize_vector_db()
    
    def _initialize_embeddings(self):
        """Initialize embeddings based on config"""
        if self.config.llm.provider == "openai":
            if not self.config.openai_api_key:
                raise ValueError("OpenAI API key not found. Check your .env file.")
            
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=self.config.openai_api_key,
                model="text-embedding-ada-002"
            )
            print("✅ OpenAI embeddings initialized")
            
        elif self.config.llm.provider == "anthropic":
            # For Claude, we'll use OpenAI embeddings but Claude for analysis
            # (Anthropic doesn't have a dedicated embedding model yet)
            if not self.config.openai_api_key:
                print("⚠️  Using Claude for LLM but need OpenAI for embeddings")
                print("   You can get a free OpenAI key just for embeddings")
                print("   Or we can use a free embedding alternative...")
                
                # Use sentence-transformers as fallback
                try:
                    from langchain_community.embeddings import HuggingFaceEmbeddings
                    self.embeddings = HuggingFaceEmbeddings(
                        model_name="all-MiniLM-L6-v2"
                    )
                    print("✅ Using free HuggingFace embeddings (all-MiniLM-L6-v2)")
                except ImportError:
                    raise ValueError("Need either OpenAI API key or sentence-transformers. Run: pip install sentence-transformers")
            else:
                self.embeddings = OpenAIEmbeddings(
                    openai_api_key=self.config.openai_api_key,
                    model="text-embedding-ada-002"
                )
                print("✅ OpenAI embeddings initialized (using with Claude)")
        else:
            raise ValueError(f"Unsupported LLM provider: {self.config.llm.provider}")
    
    def _initialize_vector_db(self):
        """Initialize ChromaDB"""
        # Create persist directory if it doesn't exist
        persist_dir = Path(self.config.vector_db.persist_directory)
        persist_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self.chroma_client = chromadb.PersistentClient(
            path=str(persist_dir)
        )
        
        # Get or create collection
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.config.vector_db.collection_name,
            metadata={"description": "WatchDogAI log embeddings"}
        )
        
        print(f"✅ ChromaDB initialized at {persist_dir}")
        print(f"   Collection: {self.config.vector_db.collection_name}")
    
    def parse_logs(self, log_data: str, source: str = "manual") -> List[LogEntry]:
        """Parse raw log data into LogEntry objects"""
        log_entries = []
        
        # Split by lines and process each
        lines = log_data.strip().split('\n')
        
        for line in lines:
            if line.strip():  # Skip empty lines
                entry = LogEntry(
                    raw_log=line,
                    source=source,
                    timestamp=datetime.now()
                )
                log_entries.append(entry)
        
        return log_entries
    
    def embed_logs(self, log_entries: List[LogEntry]) -> bool:
        """Embed log entries and store in vector database"""
        if not log_entries:
            return False
        
        try:
            # Prepare data for ChromaDB
            documents = [entry.searchable_text for entry in log_entries]
            metadatas = [entry.to_chroma_metadata() for entry in log_entries]  # Use flattened metadata
            ids = [entry.id for entry in log_entries]
            
            # Generate embeddings
            print(f"🔄 Generating embeddings for {len(log_entries)} log entries...")
            embeddings = self.embeddings.embed_documents(documents)
            
            # Store in ChromaDB
            self.collection.add(
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            print(f"✅ Successfully embedded and stored {len(log_entries)} log entries")
            return True
            
        except Exception as e:
            print(f"❌ Error embedding logs: {e}")
            return False
    
    def search_similar_logs(self, query: str, n_results: int = 5) -> List[Dict]:
        """Search for logs similar to the query"""
        try:
            # Generate query embedding
            query_embedding = self.embeddings.embed_query(query)
            
            # Search ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results
            similar_logs = []
            for i in range(len(results['documents'][0])):
                similar_logs.append({
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'similarity_score': 1 - results['distances'][0][i]  # Convert distance to similarity
                })
            
            return similar_logs
            
        except Exception as e:
            print(f"❌ Error searching logs: {e}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the log collection"""
        try:
            count = self.collection.count()
            return {
                'total_logs': count,
                'collection_name': self.config.vector_db.collection_name,
                'persist_directory': self.config.vector_db.persist_directory
            }
        except Exception as e:
            print(f"❌ Error getting collection stats: {e}")
            return {}
    
    def clear_collection(self):
        """Clear all logs from the collection (for testing)"""
        try:
            # Delete the collection and recreate it
            self.chroma_client.delete_collection(self.config.vector_db.collection_name)
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.config.vector_db.collection_name,
                metadata={"description": "WatchDogAI log embeddings"}
            )
            print("✅ Collection cleared")
        except Exception as e:
            print(f"❌ Error clearing collection: {e}")