from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class WorkflowBenchmarkCase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    input: str = Field(min_length=2, max_length=12000)
    expected_output: str | None = None
    expected_keywords: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_expectation(self):
        if not self.expected_output and not self.expected_keywords:
            raise ValueError("expected_output or expected_keywords is required")
        return self


class WorkflowBenchmarkCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    versions: list[int] = Field(min_length=2, max_length=6)
    cases: list[WorkflowBenchmarkCase] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def require_distinct_versions(self):
        if len(set(self.versions)) != len(self.versions):
            raise ValueError("versions must be distinct")
        if any(version < 1 for version in self.versions):
            raise ValueError("versions must be positive")
        return self


class WorkflowBenchmarkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    project_id: UUID | None
    workflow_id: UUID
    name: str
    status: str
    dataset: list[dict[str, Any]]
    candidate_versions: list[int]
    results: list[dict[str, Any]]
    winner_version: int | None
    duration_ms: int
    error: str | None
    created_at: datetime
    updated_at: datetime
