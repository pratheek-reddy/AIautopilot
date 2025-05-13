from pydantic import BaseModel
from typing import Dict, Any, Optional
from enum import Enum

class ContentFormat(str, Enum):
    MARKDOWN = "markdown"
    HTML = "html"
    PLAIN_TEXT = "plain_text"
    RICH_TEXT = "rich_text"

class QualityCheckLevel(str, Enum):
    BASIC = "basic"
    STANDARD = "standard"
    STRICT = "strict"

class WriterGraphConfig(BaseModel):
    # Graph settings
    max_retries: int = 3
    timeout_seconds: int = 30
    batch_size: int = 10
    
    # Content processing settings
    default_format: ContentFormat = ContentFormat.MARKDOWN
    supported_formats: list[ContentFormat] = [
        ContentFormat.MARKDOWN,
        ContentFormat.HTML,
        ContentFormat.PLAIN_TEXT
    ]
    
    # Quality check settings
    quality_check_level: QualityCheckLevel = QualityCheckLevel.STANDARD
    enable_grammar_check: bool = True
    enable_style_check: bool = True
    enable_format_check: bool = True
    
    # Performance settings
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600
    max_parallel_tasks: int = 5
    
    # Error handling settings
    retry_delay_seconds: int = 1
    max_error_retries: int = 3
    error_backoff_factor: float = 2.0
    
    # State management settings
    state_persistence: bool = True
    state_cleanup_interval: int = 86400  # 24 hours
    max_state_history: int = 100
    
    # Logging settings
    enable_debug_logging: bool = False
    log_state_transitions: bool = True
    log_performance_metrics: bool = True
    
    # Resource limits
    max_content_size_bytes: int = 10_000_000  # 10MB
    max_metadata_size_bytes: int = 1_000_000  # 1MB
    max_history_entries: int = 1000
    
    class Config:
        env_prefix = "WRITER_GRAPH_"
        case_sensitive = True 