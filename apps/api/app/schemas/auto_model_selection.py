from pydantic import BaseModel

from app.services.model_router import AITaskType


class AutoModelSelectionResponse(BaseModel):
    task: AITaskType
    model: str
    reason: str
    source: str
    sample_size: int
    average_score: float | None
    average_duration_ms: int | None
    used_fallback: bool
