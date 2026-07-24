from typing import Optional

from pydantic import BaseModel, Field


class ReviewSchema(BaseModel):
    """
    The shape we force Gemini's response into (via response_schema= in services.py).
    One schema shared across all three categories, rather than three separate
    schemas, because the fields overlap heavily and a single JSONField on
    ReviewResult is easiest to query/display generically. Category-specific
    fields are Optional and simply left null when they don't apply — the prompt
    (see prompts.py) tells the model which ones to fill in for a given category.
    """

    overall_score: int = Field(ge=0, le=10)
    summary: str
    readability: str
    best_practices: str
    top_improvements: list[str]

    # dsa
    time_complexity: Optional[str] = None
    space_complexity: Optional[str] = None

    # production
    security_notes: Optional[str] = None
    scalability_notes: Optional[str] = None

    # learning
    suggested_next_steps: Optional[list[str]] = None
