from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PromptEvaluationCase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    input: str = Field(min_length=1)
    variables: dict[str, str] = Field(default_factory=dict)
    expected_output: str | None = None
    expected_keywords: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_expectation(self):
        if not self.expected_output and not self.expected_keywords:
            raise ValueError("expected_output or expected_keywords is required")
        return self


class PromptEvaluationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    prompt_version: int | None = Field(default=None, ge=1)
    cases: list[PromptEvaluationCase] = Field(min_length=1, max_length=100)


class PromptEvaluationCaseResult(BaseModel):
    name: str
    output: str
    score: float
    passed: bool
    matched_keywords: list[str]
    missing_keywords: list[str]
    duration_ms: int


class PromptEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    project_id: UUID | None
    prompt_id: UUID
    prompt_version: int | None
    name: str
    status: str
    provider: str
    model: str
    dataset: list[dict[str, Any]]
    results: list[dict[str, Any]]
    score: float
    duration_ms: int
    error: str | None
    created_at: datetime
    updated_at: datetime
