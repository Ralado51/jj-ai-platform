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
        execution_id=None,
        asset_type=AssetType.IMAGE,
        name="generated-hero",
        description=None,
        storage_provider="s3",
        storage_path="projects/demo/generated-images/hero.png",
        public_url="https://files.example.com/jj-ai-projects/projects/demo/generated-images/hero.png",
        mime_type="image/png",
        size_bytes=None,
        checksum=None,
        asset_metadata={},
        created_at=now,
        updated_at=now,
    )
    job = ImageGenerationJob(
        id=uuid4(),
        owner_id=uuid4(),
        project_id=project_id,
        external_id=None,
        provider="free-worker",
        model="Z-Image-Turbo",
        prompt="Editorial healthcare photo",
        width=1344,
        height=768,
        seed=None,
        status="generated",
        worker_id=None,
        asset_id=asset.id,
        asset=asset,
        error=None,
        created_at=now,
        updated_at=now,
    )

    payload = ImageJobResponse.model_validate(job)

    assert payload.asset_id == asset.id
    assert payload.asset_url == asset.public_url
