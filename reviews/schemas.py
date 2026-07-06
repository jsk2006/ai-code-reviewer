from pydantic import BaseModel, Field


class ReviewSchema(BaseModel):
    overall_score: int = Field(ge=0, le=10)

    summary: str

    correctness: str

    readability: str

    efficiency: str

    best_practices: str

    top_improvements: list[str]