"""Configuration management for WatchDogAI"""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class LLMConfig:
    """LLM configuration settings"""
    provider: str = "anthropic"
    model: str = "claude-3-haiku-20240307"
    temperature: float = 0.1
    max_tokens: int = 1000


@dataclass
class VectorDBConfig:
    """Vector database configuration"""
    provider: str = "chromadb"
    persist_directory: str = "./data/vector_store"
    collection_name: str = "watchdog_logs"


@dataclass
class WatchDogConfig:
    """Main configuration class for WatchDogAI"""
    # API Keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # Component configs
    llm: LLMConfig = None
    vector_db: VectorDBConfig = None
    
    # Application settings
    log_level: str = "INFO"
    max_log_entries: int = 1000
    analysis_chunk_size: int = 5
    
    def __post_init__(self):
        """Initialize sub-configs if not provided"""
        if self.llm is None:
            self.llm = LLMConfig()
        if self.vector_db is None:
            self.vector_db = VectorDBConfig()


class ConfigManager:
    """Manages configuration loading and validation"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config/settings.yaml"
        self.config = WatchDogConfig()
        
        # Load configuration
        self._load_env()
        self._load_yaml()
        self._validate_config()
    
    def _load_env(self):
        """Load environment variables"""
        load_dotenv()
        
        # Load API keys
        self.config.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.config.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        
        # Load other env settings
        if log_level := os.getenv("LOG_LEVEL"):
            self.config.log_level = log_level
        
        if vector_db_path := os.getenv("VECTOR_DB_PATH"):
            self.config.vector_db.persist_directory = vector_db_path
    
    def _load_yaml(self):
        """Load YAML configuration file if it exists"""
        config_file = Path(self.config_path)
        
        if not config_file.exists():
            # Create default config file
            self._create_default_config()
            return
        
        try:
            with open(config_file, 'r') as f:
                yaml_config = yaml.safe_load(f) or {}
            
            # Update config with YAML values
            self._update_config_from_dict(yaml_config)
            
        except Exception as e:
            print(f"Warning: Could not load config file {config_file}: {e}")
    
    def _create_default_config(self):
        """Create a default configuration file"""
        default_config = {
            'llm': {
                'provider': 'anthropic',
                'model': 'claude-3-haiku-20240307',
                'temperature': 0.1,
                'max_tokens': 1000
            },
            'vector_db': {
                'provider': 'chromadb',
                'collection_name': 'watchdog_logs'
            },
            'application': {
                'log_level': 'INFO',
                'max_log_entries': 1000,
                'analysis_chunk_size': 5
            }
        }
        
        # Ensure config directory exists
        Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Write default config
        with open(self.config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False, indent=2)
        
        print(f"Created default config file: {self.config_path}")
    
    def _update_config_from_dict(self, config_dict: Dict[str, Any]):
        """Update configuration from dictionary"""
        # Update LLM config
        if 'llm' in config_dict:
            llm_config = config_dict['llm']
            self.config.llm.provider = llm_config.get('provider', self.config.llm.provider)
            self.config.llm.model = llm_config.get('model', self.config.llm.model)
            self.config.llm.temperature = llm_config.get('temperature', self.config.llm.temperature)
            self.config.llm.max_tokens = llm_config.get('max_tokens', self.config.llm.max_tokens)
        
        # Update vector DB config
        if 'vector_db' in config_dict:
            vdb_config = config_dict['vector_db']
            self.config.vector_db.provider = vdb_config.get('provider', self.config.vector_db.provider)
            self.config.vector_db.collection_name = vdb_config.get('collection_name', self.config.vector_db.collection_name)
        
        # Update application config
        if 'application' in config_dict:
            app_config = config_dict['application']
            self.config.log_level = app_config.get('log_level', self.config.log_level)
            self.config.max_log_entries = app_config.get('max_log_entries', self.config.max_log_entries)
            self.config.analysis_chunk_size = app_config.get('analysis_chunk_size', self.config.analysis_chunk_size)
    
    def _validate_config(self):
        """Validate configuration and provide helpful messages"""
        if not self.config.anthropic_api_key and self.config.llm.provider == "anthropic":
            print("⚠️  Warning: ANTHROPIC_API_KEY not found in environment")
            print("   Add it to your .env file: ANTHROPIC_API_KEY=your_key_here")
        
        if not self.config.openai_api_key and self.config.llm.provider == "openai":
            print("⚠️  Warning: OPENAI_API_KEY not found in environment")
            print("   Add it to your .env file: OPENAI_API_KEY=your_key_here")
    
    def get_config(self) -> WatchDogConfig:
        """Get the current configuration"""
        return self.config
    
    def print_config(self):
        """Print current configuration (hiding sensitive data)"""
        print("📋 WatchDogAI Configuration:")
        print(f"   LLM Provider: {self.config.llm.provider}")
        print(f"   LLM Model: {self.config.llm.model}")
        print(f"   Vector DB: {self.config.vector_db.provider}")
        print(f"   Log Level: {self.config.log_level}")
        
        # Show API key status without revealing the key
        if self.config.llm.provider == "anthropic":
            anthropic_status = "✅ Set" if self.config.anthropic_api_key else "❌ Missing"
            print(f"   Anthropic API Key: {anthropic_status}")
        
        if self.config.llm.provider == "openai":
            openai_status = "✅ Set" if self.config.openai_api_key else "❌ Missing"
            print(f"   OpenAI API Key: {openai_status}")


# Global config instance
_config_manager = None


def get_config() -> WatchDogConfig:
    """Get global configuration instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager.get_config()


def init_config(config_path: Optional[str] = None) -> ConfigManager:
    """Initialize configuration with optional custom path"""
    global _config_manager
    _config_manager = ConfigManager(config_path)
    return _config_manager