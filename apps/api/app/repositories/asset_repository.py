from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.enums import AssetType


class AssetRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, asset: Asset) -> Asset:
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)
        return asset

    def save(self, asset: Asset) -> Asset:
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)
        return asset

    def list_documents_by_project(
        self,
        project_id: UUID,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Asset]:
        statement = (
            select(Asset)
            .where(
                Asset.project_id == project_id,
                Asset.asset_type == AssetType.DOCUMENT,
            )
            .order_by(Asset.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())

    def count_documents_by_project(self, project_id: UUID) -> int:
        statement = select(func.count(Asset.id)).where(
            Asset.project_id == project_id,
            Asset.asset_type == AssetType.DOCUMENT,
        )
        return int(self.db.scalar(statement) or 0)

    def get_document(self, document_id: UUID) -> Asset | None:
        statement = select(Asset).where(
            Asset.id == document_id,
            Asset.asset_type == AssetType.DOCUMENT,
        )
        return self.db.scalar(statement)

    def get_document_names(self, document_ids: list[UUID]) -> dict[UUID, str]:
        if not document_ids:
            return {}

        statement = select(Asset.id, Asset.name).where(
            Asset.id.in_(document_ids),
            Asset.asset_type == AssetType.DOCUMENT,
        )
        return {document_id: name for document_id, name in self.db.execute(statement).all()}

    def delete(self, asset: Asset) -> None:
        self.db.delete(asset)
        self.db.commit()

    def flush_delete(self, asset: Asset) -> None:
        self.db.delete(asset)
        self.db.flush()
