"""WatchDogAI - LangChain-based log analysis agent"""

from .config import get_config, init_config, ConfigManager
from .embeddings import LogEmbeddings, LogEntry
from .analyzer import LogAnalyzer, SecurityRecommendation

__version__ = "0.1.0"
__all__ = [
    "get_config",
    "init_config", 
    "ConfigManager",
    "LogEmbeddings",
    "LogEntry",
    "LogAnalyzer",
    "SecurityRecommendation"
]