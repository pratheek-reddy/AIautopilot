from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.core.writer_config import ContentFormat, QualityCheckLevel

class ContentMetadata(BaseModel):
    content_type: str
    word_count: int
    character_count: int
    language: str
    created_at: datetime
    modified_at: datetime
    format: ContentFormat
    tags: List[str] = Field(default_factory=list)
    custom_metadata: Dict[str, Any] = Field(default_factory=dict)

class ContentState(BaseModel):
    original_content: str
    content_type: str
    structure: Dict[str, Any]
    processing_status: str
    metadata: ContentMetadata
    error: Optional[str] = None
    retry_count: int = 0

class FormatState(BaseModel):
    selected_format: ContentFormat
    format_parameters: Dict[str, Any]
    style_preferences: Dict[str, Any]
    output_requirements: Dict[str, Any]
    validation_rules: Dict[str, Any]
    error: Optional[str] = None

class OutputState(BaseModel):
    formatted_content: str
    quality_metrics: Dict[str, float]
    validation_results: Dict[str, bool]
    error: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    performance_metrics: Dict[str, float] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)

class WriterGraphState(BaseModel):
    content_state: Optional[ContentState] = None
    format_state: Optional[FormatState] = None
    output_state: Optional[OutputState] = None
    current_node: str
    next_node: Optional[str] = None
    error: Optional[str] = None
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    quality_check_level: QualityCheckLevel = QualityCheckLevel.STANDARD
    history: List[Dict[str, Any]] = Field(default_factory=list) 