from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from app.api.models import ContentRequest, ContentResponse, ContentStatus
from app.workflows.writer_graph import WriterGraph
from app.workflows.writer_states import WriterGraphState, ContentState
from app.core.writer_config import WriterGraphConfig, ContentFormat
from app.db.session import get_db
from app.db.models import WriterContent, WriterFormatState, WriterOutputState
from datetime import datetime
import uuid

router = APIRouter()

@router.post("/content", response_model=ContentResponse)
async def create_content(
    request: ContentRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create and process new content."""
    try:
        # Create content record
        content = WriterContent(
            task_id=str(uuid.uuid4()),
            original_content=request.content,
            content_type=request.content_type,
            format=request.format or ContentFormat.PLAIN_TEXT,
            processing_status="pending"
        )
        db.add(content)
        db.commit()
        db.refresh(content)

        # Initialize writer graph
        writer_graph = WriterGraph(WriterGraphConfig())
        
        # Create initial state
        initial_state = WriterGraphState(
            content_state=ContentState(
                original_content=request.content,
                content_type=request.content_type,
                structure={},
                processing_status="pending",
                metadata={
                    "format": request.format,
                    "style": request.style,
                    "requirements": request.requirements
                }
            ),
            current_node="content_analyzer"
        )

        # Process content in background
        background_tasks.add_task(
            process_content,
            content.id,
            initial_state,
            writer_graph,
            db
        )

        return ContentResponse(
            content_id=content.id,
            status=ContentStatus.PROCESSING,
            message="Content processing started"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/content/{content_id}", response_model=ContentResponse)
async def get_content_status(
    content_id: int,
    db: Session = Depends(get_db)
):
    """Get the status and result of content processing."""
    content = db.query(WriterContent).filter(WriterContent.id == content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    return ContentResponse(
        content_id=content.id,
        status=ContentStatus(content.processing_status),
        message="Content processing status",
        result=content.output_state.formatted_content if content.output_state else None,
        metadata=content.metadata
    )

@router.get("/content/{content_id}/format", response_model=Dict[str, Any])
async def get_content_format(
    content_id: int,
    db: Session = Depends(get_db)
):
    """Get the format state of the content."""
    content = db.query(WriterContent).filter(WriterContent.id == content_id).first()
    if not content or not content.format_state:
        raise HTTPException(status_code=404, detail="Content or format state not found")

    return {
        "format": content.format_state.selected_format,
        "parameters": content.format_state.format_parameters,
        "style": content.format_state.style_preferences,
        "requirements": content.format_state.output_requirements
    }

@router.get("/content/{content_id}/quality", response_model=Dict[str, Any])
async def get_content_quality(
    content_id: int,
    db: Session = Depends(get_db)
):
    """Get the quality metrics of the content."""
    content = db.query(WriterContent).filter(WriterContent.id == content_id).first()
    if not content or not content.output_state:
        raise HTTPException(status_code=404, detail="Content or output state not found")

    return {
        "metrics": content.output_state.quality_metrics,
        "validation": content.output_state.validation_results,
        "warnings": content.output_state.warnings,
        "performance": content.output_state.performance_metrics
    }

async def process_content(
    content_id: int,
    state: WriterGraphState,
    writer_graph: WriterGraph,
    db: Session
):
    """Process content using the writer graph."""
    try:
        # Run the graph
        result = writer_graph.graph.invoke(state)

        # Update content record
        content = db.query(WriterContent).filter(WriterContent.id == content_id).first()
        if not content:
            return

        # Update content state
        content.processing_status = "completed"
        content.structure = result.content_state.structure
        content.metadata = result.content_state.metadata.dict()

        # Create format state
        format_state = WriterFormatState(
            content_id=content_id,
            selected_format=result.format_state.selected_format,
            format_parameters=result.format_state.format_parameters,
            style_preferences=result.format_state.style_preferences,
            output_requirements=result.format_state.output_requirements,
            validation_rules=result.format_state.validation_rules
        )
        db.add(format_state)

        # Create output state
        output_state = WriterOutputState(
            content_id=content_id,
            formatted_content=result.output_state.formatted_content,
            quality_metrics=result.output_state.quality_metrics,
            validation_results=result.output_state.validation_results,
            warnings=result.output_state.warnings,
            performance_metrics=result.output_state.performance_metrics,
            quality_check_level=result.quality_check_level
        )
        db.add(output_state)

        db.commit()

    except Exception as e:
        # Update content with error
        content = db.query(WriterContent).filter(WriterContent.id == content_id).first()
        if content:
            content.processing_status = "failed"
            content.error = str(e)
            db.commit() 