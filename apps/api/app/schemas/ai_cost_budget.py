from __future__ import annotations

from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

BudgetScope = Literal["global", "project", "workflow"]


class AICostBudgetCreateRequest(BaseModel):
    scope_type: BudgetScope
    scope_id: UUID | None = None
    name: str = Field(min_length=1, max_length=150)
    monthly_limit: Decimal = Field(gt=0)
    warning_threshold_percent: int = Field(default=80, ge=1, le=100)
    critical_threshold_percent: int = Field(default=100, ge=1, le=200)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_scope(self):
        if self.scope_type == "global" and self.scope_id is not None:
            raise ValueError("Global budget must not have scope_id")
        if self.scope_type != "global" and self.scope_id is None:
            raise ValueError("Project and workflow budgets require scope_id")
        if self.warning_threshold_percent >= self.critical_threshold_percent:
            raise ValueError("Warning threshold must be lower than critical threshold")
        return self


class AICostBudgetUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    monthly_limit: Decimal | None = Field(default=None, gt=0)
    warning_threshold_percent: int | None = Field(default=None, ge=1, le=100)
    critical_threshold_percent: int | None = Field(default=None, ge=1, le=200)
    is_active: bool | None = None


class AICostBudgetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scope_type: BudgetScope
    scope_id: UUID | None
    name: str
    monthly_limit: Decimal
    warning_threshold_percent: int
    critical_threshold_percent: int
    is_active: bool


class AICostBudgetStatusResponse(AICostBudgetResponse):
    current_spend: Decimal
    usage_percent: float
    remaining: Decimal
    status: Literal["healthy", "warning", "critical"]
