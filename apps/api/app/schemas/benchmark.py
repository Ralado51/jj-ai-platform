from __future__ import annotations

from pydantic import BaseModel, Field

from app.services.model_router import AITaskType


class BenchmarkRunRequest(BaseModel):
    task: AITaskType = AITaskType.GENERAL
    system_prompt: str = Field(
        default="Você é um assistente útil e objetivo.",
        min_length=1,
        max_length=8000,
    )
    prompt: str = Field(min_length=2, max_length=12000)
    models: list[str] = Field(min_length=2, max_length=6)


class BenchmarkScoresResponse(BaseModel):
    hook: float
    storytelling: float
    clarity: float
    originality: float
    call_to_action: float
    structure: float
    overall: float


class BenchmarkModelResultResponse(BaseModel):
    model: str
    duration_ms: int
    response: str
    estimated_tokens: int
    success: bool
    error: str | None = None
    scores: BenchmarkScoresResponse | None = None


class BenchmarkRunResponse(BaseModel):
    task: AITaskType
    winner: str | None
    results: list[BenchmarkModelResultResponse]
