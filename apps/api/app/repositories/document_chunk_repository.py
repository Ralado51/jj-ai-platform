from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.document_chunk import DocumentChunk


class DocumentChunkRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def replace_for_document(
        self,
        *,
        document_id: UUID,
        project_id: UUID,
        chunks: list[str],
    ) -> list[DocumentChunk]:
        self.db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
        records = [
            DocumentChunk(
                document_id=document_id,
                project_id=project_id,
                chunk_index=index,
                content=content,
                character_count=len(content),
            )
            for index, content in enumerate(chunks)
        ]
        self.db.add_all(records)
        self.db.commit()
        for record in records:
            self.db.refresh(record)
        return records

    def list_for_document(self, document_id: UUID) -> list[DocumentChunk]:
        statement = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        return list(self.db.scalars(statement).all())

    def update_embeddings(
        self,
        *,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
    ) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("Chunk and embedding counts must match")
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            chunk.embedding = embedding
        self.db.commit()

    def semantic_search(
        self,
        *,
        project_id: UUID,
        query_embedding: list[float],
        limit: int,
    ) -> list[tuple[DocumentChunk, float]]:
        distance = DocumentChunk.embedding.cosine_distance(query_embedding)
        statement = (
            select(DocumentChunk, distance.label("distance"))
            .where(
                DocumentChunk.project_id == project_id,
                DocumentChunk.embedding.is_not(None),
            )
            .order_by(distance.asc())
            .limit(limit)
        )
        rows = self.db.execute(statement).all()
        return [
            (chunk, max(0.0, min(1.0, 1.0 - float(value))))
            for chunk, value in rows
        ]
