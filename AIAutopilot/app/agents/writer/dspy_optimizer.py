from dspy import BootstrapFewShot, BootstrapFinetune
from .dspy_modules import EmailGenerator, SOPGenerator, SummaryGenerator

class ContentOptimizer:
    """Optimizes DSPy modules using few-shot examples and fine-tuning."""
    
    def __init__(self, telemetry_client=None):
        self.telemetry_client = telemetry_client
        self.email_generator = EmailGenerator()
        self.sop_generator = SOPGenerator()
        self.summary_generator = SummaryGenerator()
        
        # Initialize optimizers
        self.email_optimizer = BootstrapFewShot(metric=self._evaluate_email)
        self.sop_optimizer = BootstrapFewShot(metric=self._evaluate_sop)
        self.summary_optimizer = BootstrapFewShot(metric=self._evaluate_summary)
    
    def _evaluate_email(self, example, pred, trace=None):
        """Evaluate email quality based on structure, tone, and clarity."""
        score = 0.0
        
        # Check structure
        if pred.subject and pred.greeting and pred.body and pred.closing:
            score += 0.4
        
        # Check tone appropriateness
        if pred.body and example.tone.lower() in pred.body.lower():
            score += 0.3
        
        # Check clarity
        if len(pred.body.split()) > 50:  # Minimum length for clarity
            score += 0.3
            
        return score
    
    def _evaluate_sop(self, example, pred, trace=None):
        """Evaluate SOP quality based on completeness and clarity."""
        score = 0.0
        
        # Check structure
        if pred.title and pred.purpose and pred.steps:
            score += 0.4
        
        # Check prerequisites
        if pred.prerequisites:
            score += 0.3
        
        # Check warnings and references
        if pred.warnings or pred.references:
            score += 0.3
            
        return score
    
    def _evaluate_summary(self, example, pred, trace=None):
        """Evaluate summary quality based on coverage and conciseness."""
        score = 0.0
        
        # Check structure
        if pred.overview and pred.main_points and pred.conclusions:
            score += 0.4
        
        # Check key points coverage
        covered_points = sum(1 for point in example.key_points if point.lower() in pred.main_points.lower())
        if covered_points > 0:
            score += 0.3 * (covered_points / len(example.key_points))
        
        # Check next steps
        if pred.next_steps:
            score += 0.3
            
        return score
    
    def optimize_email_generator(self, examples):
        """Optimize email generator using few-shot examples."""
        self.email_generator = self.email_optimizer.bootstrap(
            self.email_generator,
            examples=examples
        )
        if self.telemetry_client:
            self.telemetry_client.capture_optimization("email_generator")
    
    def optimize_sop_generator(self, examples):
        """Optimize SOP generator using few-shot examples."""
        self.sop_generator = self.sop_optimizer.bootstrap(
            self.sop_generator,
            examples=examples
        )
        if self.telemetry_client:
            self.telemetry_client.capture_optimization("sop_generator")
    
    def optimize_summary_generator(self, examples):
        """Optimize summary generator using few-shot examples."""
        self.summary_generator = self.summary_optimizer.bootstrap(
            self.summary_generator,
            examples=examples
        )
        if self.telemetry_client:
            self.telemetry_client.capture_optimization("summary_generator") 