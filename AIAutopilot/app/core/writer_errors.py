from typing import Optional, Dict, Any

class WriterGraphError(Exception):
    """Base exception for WriterGraph errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

class ContentAnalysisError(WriterGraphError):
    """Error during content analysis."""
    pass

class FormatSelectionError(WriterGraphError):
    """Error during format selection."""
    pass

class FormattingError(WriterGraphError):
    """Error during content formatting."""
    pass

class QualityCheckError(WriterGraphError):
    """Error during quality check."""
    pass

class StateTransitionError(WriterGraphError):
    """Error during state transition."""
    pass

class ValidationError(WriterGraphError):
    """Error during content validation."""
    pass

class ResourceLimitError(WriterGraphError):
    """Error when resource limits are exceeded."""
    pass

class ConfigurationError(WriterGraphError):
    """Error in graph configuration."""
    pass

class IntegrationError(WriterGraphError):
    """Error during integration with other components."""
    pass

class RetryableError(WriterGraphError):
    """Error that can be retried."""
    pass

class FatalError(WriterGraphError):
    """Error that cannot be retried."""
    pass 