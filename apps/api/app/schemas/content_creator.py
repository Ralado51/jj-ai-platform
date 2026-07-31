from __future__ import annotations

from pydantic import BaseModel, Field


class ContentCreatorBriefing(BaseModel):
    tema: str = Field(min_length=3, max_length=300)
    publico: str = Field(min_length=3, max_length=500)
    plataforma: str = Field(min_length=2, max_length=100)
    objetivo: str = Field(min_length=3, max_length=300)
    formato: str = Field(min_length=2, max_length=100)
    tom: str = Field(min_length=2, max_length=100)
    duracao: str = Field(min_length=2, max_length=100)
    cta: str = Field(min_length=2, max_length=300)


class ContentValidationResponse(BaseModel):
    is_valid: bool
    issues: list[str]


class PromptEvaluationScoresResponse(BaseModel):
    hook: float
    storytelling: float
    clarity: float
    originality: float
    call_to_action: float
    structure: float
    overall: float


class PromptEvaluationResponse(BaseModel):
    scores: PromptEvaluationScoresResponse
    issues: list[str]
    strengths: list[str]
    passed: bool


class ContentCreatorResponse(BaseModel):
    content: str
    provider: str
    model: str
    refined: bool
    validation: ContentValidationResponse
    evaluation: PromptEvaluationResponse
