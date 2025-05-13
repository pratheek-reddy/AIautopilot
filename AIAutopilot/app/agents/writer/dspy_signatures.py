from dspy import Signature, InputField, OutputField
from typing import Optional, List

class EmailSignature(Signature):
    """Signature for generating professional emails."""
    meeting_notes: str = InputField(desc="Raw meeting notes to be summarized")
    audience: str = InputField(desc="Target audience for the email (e.g., 'management', 'team', 'stakeholders')")
    tone: str = InputField(desc="Desired tone of the email (e.g., 'formal', 'casual', 'urgent')")
    
    subject: str = OutputField(desc="Clear and concise email subject line")
    greeting: str = OutputField(desc="Appropriate greeting based on audience")
    body: str = OutputField(desc="Well-structured email body with key points and action items")
    closing: str = OutputField(desc="Professional closing statement")
    email_signature: str = OutputField(desc="Email signature block")

class SOPSignature(Signature):
    """Signature for generating Standard Operating Procedures."""
    process_description: str = InputField(desc="Description of the process to document")
    target_audience: str = InputField(desc="Intended users of the SOP")
    complexity_level: str = InputField(desc="Technical complexity level (basic, intermediate, advanced)")
    
    title: str = OutputField(desc="Clear and descriptive SOP title")
    purpose: str = OutputField(desc="Purpose and scope of the procedure")
    prerequisites: List[str] = OutputField(desc="Required knowledge, tools, or access")
    steps: List[str] = OutputField(desc="Numbered steps with clear instructions")
    warnings: List[str] = OutputField(desc="Important warnings or cautions")
    references: List[str] = OutputField(desc="Related documents or resources")

class SummarySignature(Signature):
    """Signature for generating executive summaries."""
    content: str = InputField(desc="Content to be summarized")
    target_length: str = InputField(desc="Desired length (e.g., 'brief', 'detailed')")
    key_points: List[str] = InputField(desc="Specific points that must be included")
    
    overview: str = OutputField(desc="High-level overview of the content")
    main_points: List[str] = OutputField(desc="Key points from the content")
    conclusions: str = OutputField(desc="Main conclusions or recommendations")
    next_steps: Optional[List[str]] = OutputField(desc="Recommended next steps or actions") 