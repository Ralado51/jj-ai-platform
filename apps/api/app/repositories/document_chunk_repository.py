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
