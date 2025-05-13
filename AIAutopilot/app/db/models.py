from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Enum as SQLEnum, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
from app.core.writer_config import ContentFormat, QualityCheckLevel

Base = declarative_base()

class TaskStatus(str, Enum):
    PENDING = "pending"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class Task(Base):
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