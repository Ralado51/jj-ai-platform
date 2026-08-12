from datetime import datetime, timezone
from uuid import uuid4

from app.models.asset import Asset
from app.models.enums import AssetType
from app.models.image_generation_job import ImageGenerationJob
from app.schemas.image_jobs import ImageJobResponse


def test_image_job_response_exposes_asset_url() -> None:
    project_id = uuid4()
    now = datetime.now(timezone.utc)
    asset = Asset(
        id=uuid4(),
        project_id=project_id,
        asset_type=AssetType.IMAGE,
        name="generated-hero",
        storage_provider="s3",
        storage_path="projects/demo/generated-images/hero.png",
        public_url="https://files.example.com/jj-ai-projects/projects/demo/generated-images/hero.png",
        created_at=now,
        updated_at=now,
    )
    job = ImageGenerationJob(
        id=uuid4(),
        owner_id=uuid4(),
        project_id=project_id,
        prompt="Editorial healthcare photo",
        status="generated",
        asset_id=asset.id,
        asset=asset,
        created_at=now,
        updated_at=now,
    )

    payload = ImageJobResponse.model_validate(job)

    assert payload.asset_id == asset.id
    assert payload.asset_url == asset.public_url
