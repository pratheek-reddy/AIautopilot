from typing import Dict, Any, Optional, List, Tuple
from langgraph.graph import StateGraph, END
from app.workflows.writer_states import (
    WriterGraphState,
    ContentState,
    FormatState,
    OutputState,
    ContentMetadata
)
from app.core.writer_config import (
    WriterGraphConfig,
    ContentFormat,
    QualityCheckLevel
)
from app.core.writer_errors import (
    ContentAnalysisError,
    FormatSelectionError,
    FormattingError,
    QualityCheckError
)
from datetime import datetime
import magic
import markdown
from bs4 import BeautifulSoup

class WriterGraph:
    def __init__(self, config: Optional[WriterGraphConfig] = None):
        self.config = config or WriterGraphConfig()
        self.graph = self._create_graph()

    def _create_graph(self) -> StateGraph:
        """Create the writer graph with nodes and edges."""
        # Create the state graph
        graph = StateGraph(WriterGraphState)

        # Add nodes
        graph.add_node("content_analyzer", self._analyze_content)
        graph.add_node("format_selector", self._select_format)
        graph.add_node("content_formatter", self._format_content)
        graph.add_node("quality_checker", self._check_quality)
        graph.add_node("metadata_generator", self._generate_metadata)

        # Add edges
        graph.add_edge("content_analyzer", "format_selector")
        graph.add_edge("format_selector", "content_formatter")
        graph.add_edge("content_formatter", "quality_checker")
        graph.add_conditional_edges(
            "quality_checker",
            self._quality_check_condition,
            path_map={
                "metadata_generator": "metadata_generator",
                "content_formatter": "content_formatter"
            }
        )
        graph.add_edge("metadata_generator", END)

        # Set entry and finish points
        graph.set_entry_point("content_analyzer")
        graph.set_finish_point("metadata_generator")

        return graph

    def _analyze_content(self, state: WriterGraphState) -> WriterGraphState:
        """Analyze content structure and requirements."""
        try:
            # Extract content metadata
            content = state.content_state.original_content
            if not content:
                state.content_state.error = "Content is empty"
                state.content_state.processing_status = "failed"
                return state
            word_count = len(content.split())
            char_count = len(content)
            
            # Detect language (using a simple heuristic for now)
            language = "en"  # Default to English
            
            # Update content state
            state.content_state.structure = {
                "word_count": word_count,
                "character_count": char_count,
                "language": language,
                "sections": self._detect_sections(content),
                "key_topics": self._extract_topics(content)
            }
            
            state.content_state.processing_status = "analyzed"
            return state
            
        except Exception as e:
            state.content_state.error = str(e)
            state.content_state.processing_status = "failed"
            return state

    def _detect_sections(self, content: str) -> List[Dict[str, Any]]:
        """Detect content sections based on headers and paragraphs."""
        sections = []
        current_section = {"title": "Introduction", "content": "", "level": 1}
        
        for line in content.split('\n'):
            if line.startswith('#'):
                # Save previous section
                if current_section["content"]:
                    sections.append(current_section)
                
                # Start new section
                level = len(line.split()[0])
                title = line.lstrip('#').strip()
                current_section = {
                    "title": title,
                    "content": "",
                    "level": level
                }
            else:
                current_section["content"] += line + "\n"
        
        # Add last section
        if current_section["content"]:
            sections.append(current_section)
            
        return sections

    def _extract_topics(self, content: str) -> List[str]:
        """Extract main topics from content."""
        # Simple implementation: extract words that appear frequently
        words = content.lower().split()
        word_freq = {}
        
        for word in words:
            if len(word) > 3:  # Skip short words
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get top 5 most frequent words as topics
        topics = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        return [topic[0] for topic in topics]

    def _select_format(self, state: WriterGraphState) -> WriterGraphState:
        """Select appropriate format based on content and requirements."""
        try:
            content = state.content_state.original_content
            requirements = state.content_state.metadata.custom_metadata.get("requirements", {})
            
            # Default to markdown if no specific requirements
            selected_format = ContentFormat.MARKDOWN
            
            # Check for HTML-specific requirements
            if requirements.get("html_required", False):
                selected_format = ContentFormat.HTML
            # Check for rich text requirements
            elif requirements.get("rich_text", False):
                selected_format = ContentFormat.RICH_TEXT
            # Check for plain text requirements
            elif requirements.get("plain_text", False):
                selected_format = ContentFormat.PLAIN_TEXT
            
            # Create format state
            state.format_state = FormatState(
                selected_format=selected_format,
                format_parameters={
                    "indentation": requirements.get("indentation", "  "),
                    "line_length": requirements.get("line_length", 80),
                    "header_style": requirements.get("header_style", "atx")
                },
                style_preferences=state.content_state.metadata.custom_metadata.get("style", {}),
                output_requirements=requirements,
                validation_rules=self._get_validation_rules(selected_format)
            )
            
            return state
            
        except Exception as e:
            state.content_state.error = str(e)
            state.content_state.processing_status = "failed"
            return state

    def _get_validation_rules(self, format: ContentFormat) -> Dict[str, Any]:
        """Get validation rules for the selected format."""
        base_rules = {
            "max_line_length": 100,
            "min_section_length": 50,
            "require_headers": True
        }
        
        format_specific_rules = {
            ContentFormat.MARKDOWN: {
                "valid_headers": ["#", "##", "###"],
                "valid_list_markers": ["-", "*", "+"],
                "valid_code_blocks": ["```", "~~~"]
            },
            ContentFormat.HTML: {
                "valid_tags": ["p", "h1", "h2", "h3", "ul", "ol", "li", "code"],
                "require_closing_tags": True,
                "valid_attributes": ["class", "id", "style"]
            },
            ContentFormat.RICH_TEXT: {
                "valid_styles": ["bold", "italic", "underline"],
                "valid_alignments": ["left", "center", "right"],
                "valid_colors": ["black", "blue", "red", "green"]
            },
            ContentFormat.PLAIN_TEXT: {
                "max_line_length": 80,
                "allow_special_chars": False,
                "require_line_breaks": True
            }
        }
        
        return {**base_rules, **format_specific_rules.get(format, {})}

    def _format_content(self, state: WriterGraphState) -> WriterGraphState:
        """Format content according to selected format."""
        try:
            content = state.content_state.original_content
            format = state.format_state.selected_format
            params = state.format_state.format_parameters
            
            formatted_content = ""
            
            if format == ContentFormat.MARKDOWN:
                formatted_content = self._format_markdown(content, params)
            elif format == ContentFormat.HTML:
                formatted_content = self._format_html(content, params)
            elif format == ContentFormat.RICH_TEXT:
                formatted_content = self._format_rich_text(content, params)
            else:  # PLAIN_TEXT
                formatted_content = self._format_plain_text(content, params)
            
            # Create output state
            state.output_state = OutputState(
                formatted_content=formatted_content,
                quality_metrics=self._calculate_quality_metrics(formatted_content),
                validation_results=self._validate_content(formatted_content, state.format_state.validation_rules),
                warnings=[],
                performance_metrics={
                    "processing_time": 0.0,  # TODO: Implement actual timing
                    "retry_count": 0
                }
            )
            
            return state
            
        except Exception as e:
            state.content_state.error = str(e)
            state.content_state.processing_status = "failed"
            return state

    def _format_markdown(self, content: str, params: Dict[str, Any]) -> str:
        """Format content as Markdown."""
        formatted = []
        current_section = []
        
        for line in content.split('\n'):
            if line.startswith('#'):
                # Process previous section
                if current_section:
                    formatted.extend(self._format_markdown_section(current_section, params))
                    current_section = []
                
                # Add header
                formatted.append(line)
            else:
                current_section.append(line)
        
        # Process last section
        if current_section:
            formatted.extend(self._format_markdown_section(current_section, params))
        
        return '\n'.join(formatted)

    def _format_markdown_section(self, section: List[str], params: Dict[str, Any]) -> List[str]:
        """Format a section of Markdown content."""
        formatted = []
        current_paragraph = []
        
        for line in section:
            if line.strip():
                current_paragraph.append(line)
            else:
                if current_paragraph:
                    # Format paragraph
                    paragraph = ' '.join(current_paragraph)
                    # Apply line length limit
                    if len(paragraph) > params.get("line_length", 80):
                        words = paragraph.split()
                        current_line = []
                        for word in words:
                            if len(' '.join(current_line + [word])) <= params.get("line_length", 80):
                                current_line.append(word)
                            else:
                                formatted.append(' '.join(current_line))
                                current_line = [word]
                        if current_line:
                            formatted.append(' '.join(current_line))
                    else:
                        formatted.append(paragraph)
                    current_paragraph = []
                formatted.append('')
        
        # Process last paragraph
        if current_paragraph:
            formatted.append(' '.join(current_paragraph))
        
        return formatted

    def _format_html(self, content: str, params: Dict[str, Any]) -> str:
        """Format content as HTML."""
        formatted = ['<!DOCTYPE html>', '<html>', '<body>']
        
        for line in content.split('\n'):
            if line.startswith('#'):
                level = len(line.split()[0])
                text = line.lstrip('#').strip()
                formatted.append(f'<h{level}>{text}</h{level}>')
            else:
                formatted.append(f'<p>{line}</p>')
        
        formatted.extend(['</body>', '</html>'])
        return '\n'.join(formatted)

    def _format_rich_text(self, content: str, params: Dict[str, Any]) -> str:
        """Format content as Rich Text."""
        formatted = []
        
        for line in content.split('\n'):
            if line.startswith('#'):
                level = len(line.split()[0])
                text = line.lstrip('#').strip()
                formatted.append(f'<h{level} style="font-weight: bold;">{text}</h{level}>')
            else:
                formatted.append(f'<p style="margin: 10px 0;">{line}</p>')
        
        return '\n'.join(formatted)

    def _format_plain_text(self, content: str, params: Dict[str, Any]) -> str:
        """Format content as Plain Text."""
        formatted = []
        current_line = []
        
        for word in content.split():
            if len(' '.join(current_line + [word])) <= params.get("line_length", 80):
                current_line.append(word)
            else:
                formatted.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            formatted.append(' '.join(current_line))
        
        return '\n'.join(formatted)

    def _calculate_quality_metrics(self, content: str) -> Dict[str, float]:
        """Calculate quality metrics for the content."""
        return {
            "overall_score": 0.0,  # TODO: Implement actual scoring
            "readability_score": 0.0,
            "grammar_score": 0.0,
            "style_score": 0.0,
            "format_score": 0.0
        }

    def _validate_content(self, content: str, rules: Dict[str, Any]) -> Dict[str, bool]:
        """Validate content against format rules."""
        # For now, always return valid. In the future, add real checks.
        return {
            "is_valid": True,
            "grammar_valid": True,
            "style_valid": True,
            "format_valid": True
        }

    def _check_quality(self, state: WriterGraphState) -> WriterGraphState:
        """Check the quality of the formatted content."""
        try:
            content = state.output_state.formatted_content
            quality_level = state.quality_check_level
            
            # Perform quality checks
            quality_metrics = self._perform_quality_checks(content, quality_level)
            state.output_state.quality_metrics.update(quality_metrics)
            
            # Add warnings if any
            warnings = self._get_quality_warnings(quality_metrics)
            state.output_state.warnings.extend(warnings)
            
            state.current_node = "quality_checker"
            state.next_node = "metadata_generator"

        except Exception as e:
            raise QualityCheckError(f"Quality check failed: {str(e)}")

        return state

    def _quality_check_condition(self, state: WriterGraphState) -> str:
        """Determine the next node based on quality check results."""
        if state.output_state.quality_metrics.get("overall_score", 0) >= 0.8:
            return "metadata_generator"
        elif state.content_state.retry_count < self.config.max_retries:
            state.content_state.retry_count += 1
            return "content_formatter"
        else:
            return "metadata_generator"

    def _generate_metadata(self, state: WriterGraphState) -> WriterGraphState:
        """Generate final metadata for the content."""
        try:
            # Update metadata with final information
            state.content_state.metadata.modified_at = datetime.utcnow()
            state.content_state.metadata.format = state.format_state.selected_format
            
            # Add performance metrics
            state.output_state.performance_metrics = {
                "processing_time": (datetime.utcnow() - state.start_time).total_seconds(),
                "retry_count": state.content_state.retry_count
            }
            
            # Mark processing as completed
            state.content_state.processing_status = "completed"

            state.current_node = "metadata_generator"
            state.end_time = datetime.utcnow()

        except Exception as e:
            state.error = str(e)

        return state

    # Helper methods
    def _perform_quality_checks(self, content: str, quality_level: QualityCheckLevel) -> Dict[str, float]:
        """Perform quality checks on the content."""
        # TODO: Implement quality checks
        return {"overall_score": 1.0}

    def _get_quality_warnings(self, quality_metrics: Dict[str, float]) -> List[str]:
        """Get warnings based on quality metrics."""
        # TODO: Implement quality warnings
        return [] 