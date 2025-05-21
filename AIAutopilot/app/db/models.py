"""
Database Models Module.

This module defines the SQLAlchemy ORM models for the AI Autopilot system's
persistent storage. It includes models for task tracking, content management,
and writer workflow states.

Key model categories:
- Task Management (Task, TaskStatus)
- Content Management (WriterContent)
- Writer Workflow States (WriterFormatState, WriterOutputState)

The models use SQLAlchemy's declarative base and include relationships
for maintaining referential integrity and easy navigation between
related records.
"""

from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Enum as SQLEnum, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
from app.core.writer_config import ContentFormat, QualityCheckLevel

Base = declarative_base()

class TaskStatus(str, Enum):
    """
    Enumeration of possible task states in the database.
    
    Tracks the complete lifecycle of a task from creation through
    approval (if required) to completion or failure.
    """
    PENDING = "pending"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class Task(Base):
    """
    Task tracking and management model.
    
    Stores information about automation tasks, including their current status,
    execution plan, and results. Maintains timestamps for tracking task lifecycle
    and relationships with generated content.

    Attributes:
        id: Unique task identifier
        status: Current task status
        request: Original task request
        require_approval: Whether task needs approval before execution
        script_type: Type of script to be generated
        plan: JSON-encoded execution plan
        result: Task execution result
        error: Error message if task failed
        created_at: Task creation timestamp
        updated_at: Last update timestamp
        writer_content: Related writer content items
    """
    __tablename__ = "tasks"

    id = Column(String, primary_key=True)
    status = Column(String, nullable=False)
    request = Column(String, nullable=False)
    require_approval = Column(Boolean, default=False)
    script_type = Column(String, nullable=True)  # Can be 'powershell', 'bash', or 'azurecli'
    plan = Column(JSON, nullable=True)
    result = Column(String, nullable=True)
    error = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    writer_content = relationship("WriterContent", back_populates="task")

class WriterContent(Base):
    """
    Content management and tracking model.
    
    Stores content being processed by the writer workflow, including
    metadata about the content and its processing status. Maintains
    relationships with format and output states.

    Attributes:
        id: Unique content identifier
        task_id: Associated task ID
        original_content: Raw input content
        content_type: Type of content being processed
        format: Desired output format
        word_count: Content word count
        character_count: Content character count
        language: Content language
        created_at: Content creation timestamp
        modified_at: Last modification timestamp
        content_metadata: Additional content metadata
        structure: Content structure information
        processing_status: Current processing state
        error: Error message if processing failed
        retry_count: Number of processing attempts
        task: Related task
        format_state: Related format state
        output_state: Related output state
    """
    __tablename__ = "writer_contents"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    original_content = Column(String)
    content_type = Column(String)
    format = Column(SQLEnum(ContentFormat))
    word_count = Column(Integer, nullable=True)
    character_count = Column(Integer, nullable=True)
    language = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    modified_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    content_metadata = Column(JSON)
    structure = Column(JSON)
    processing_status = Column(String)
    error = Column(String, nullable=True)
    retry_count = Column(Integer, default=0)

    # Relationships
    task = relationship("Task", back_populates="writer_content")
    format_state = relationship("WriterFormatState", back_populates="content", uselist=False)
    output_state = relationship("WriterOutputState", back_populates="content", uselist=False)

class WriterFormatState(Base):
    """
    Content formatting state model.
    
    Tracks the formatting preferences and requirements for content
    being processed by the writer workflow. Includes validation rules
    and style preferences.

    Attributes:
        id: Unique format state identifier
        content_id: Associated content ID
        selected_format: Chosen output format
        format_parameters: Format-specific parameters
        style_preferences: Style configuration
        output_requirements: Output specifications
        validation_rules: Content validation rules
        error: Error message if formatting failed
        content: Related content item
    """
    __tablename__ = "writer_format_states"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("writer_contents.id"))
    selected_format = Column(SQLEnum(ContentFormat))
    format_parameters = Column(JSON)
    style_preferences = Column(JSON)
    output_requirements = Column(JSON)
    validation_rules = Column(JSON)
    error = Column(String, nullable=True)

    # Relationships
    content = relationship("WriterContent", back_populates="format_state")

class WriterOutputState(Base):
    """
    Content output state model.
    
    Stores the results of content processing, including the formatted
    content, quality metrics, and validation results. Tracks performance
    metrics and any warnings generated during processing.

    Attributes:
        id: Unique output state identifier
        content_id: Associated content ID
        formatted_content: Processed content
        quality_metrics: Content quality measurements
        validation_results: Validation check results
        error: Error message if validation failed
        warnings: Processing warnings
        performance_metrics: Processing performance data
        quality_check_level: Level of quality checking applied
        created_at: Output creation timestamp
        content: Related content item
    """
    __tablename__ = "writer_output_states"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("writer_contents.id"))
    formatted_content = Column(String)
    quality_metrics = Column(JSON)
    validation_results = Column(JSON)
    error = Column(String, nullable=True)
    warnings = Column(JSON)
    performance_metrics = Column(JSON)
    quality_check_level = Column(SQLEnum(QualityCheckLevel))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    content = relationship("WriterContent", back_populates="output_state") 