from pathlib import Path


def test_conversation_migration_extends_current_head() -> None:
    migration = Path("alembic/versions/20260730_01_add_conversations.py").read_text(encoding="utf-8")
    assert 'down_revision = "20260728_03"' in migration
