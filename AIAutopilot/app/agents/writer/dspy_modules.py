from dspy import Module, Predict
from .dspy_signatures import EmailSignature, SOPSignature, SummarySignature

class EmailGenerator(Module):
    """DSPy module for generating professional emails."""
    
    def __init__(self):
        super().__init__()
        self.predict = Predict(EmailSignature)
    
    def forward(self, meeting_notes: str, audience: str, tone: str):
        """Generate a professional email from meeting notes."""
        result = self.predict(
            meeting_notes=meeting_notes,
            audience=audience,
            tone=tone
        )
        return result

class SOPGenerator(Module):
    """DSPy module for generating Standard Operating Procedures."""
    
    def __init__(self):
        super().__init__()
        self.predict = Predict(SOPSignature)
    
    def forward(self, process_description: str, target_audience: str, complexity_level: str):
        """Generate a Standard Operating Procedure."""
        result = self.predict(
            process_description=process_description,
            target_audience=target_audience,
            complexity_level=complexity_level
        )
        return result

class SummaryGenerator(Module):
    """DSPy module for generating executive summaries."""
    
    def __init__(self):
        super().__init__()
        self.predict = Predict(SummarySignature)
    
    def forward(self, content: str, target_length: str, key_points: list):
        """Generate an executive summary."""
        result = self.predict(
            content=content,
            target_length=target_length,
            key_points=key_points
        )
        return result 