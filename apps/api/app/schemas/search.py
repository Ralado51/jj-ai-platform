from uuid import UUID

from pydantic import BaseModel, Field


class SemanticSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)


class SemanticSearchResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    project_id: UUID
    chunk_index: int
    content: str
    score: float


class SemanticSearchResponse(BaseModel):
    project_id: UUID
    query: str
    provider: str
    model: str
    total: int
    results: list[SemanticSearchResult]


class RagAnswerRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)
    min_score: float = Field(default=0.2, ge=0.0, le=1.0)


class RagSource(BaseModel):
    chunk_id: UUID
    document_id: UUID
    document_name: str
    chunk_index: int
    score: float
    snippet: str


class RagAnswerResponse(BaseModel):
    project_id: UUID
    question: str
    answer: str
    chat_provider: str
    chat_model: str
    embedding_provider: str
    embedding_model: str
    sources: list[RagSource]
