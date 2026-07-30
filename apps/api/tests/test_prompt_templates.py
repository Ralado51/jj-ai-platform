from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.user import UserRole
from app.schemas.prompt_template import PromptTemplateCreate, PromptTemplateUpdate
from app.services.prompt_template_service import PromptTemplateService


class FakePromptTemplateRepository:
    def __init__(self) -> None:
        self.items = {}
        self.db = SimpleNamespace(rollback=lambda: None)

    def create(self, data: PromptTemplateCreate, owner_id):
        template = SimpleNamespace(
            id=uuid4(),
            owner_id=owner_id,
            project_id=data.project_id,
            name=data.name,
            description=data.description,
            category=data.category,
            content=data.content,
            variables=data.variables,
            is_public=data.is_public,
            is_favorite=data.is_favorite,
            is_active=data.is_active,
            metadata_=data.metadata,
        )
        self.items[template.id] = template
        return template

    def list(self, *, user_id, project_id=None, category=None, favorite=None, search=None, include_inactive=False, offset=0, limit=100):
        visible = [item for item in self.items.values() if item.owner_id == user_id or item.is_public]
        if project_id is not None:
            visible = [item for item in visible if item.project_id in (None, project_id)]
        if category is not None:
            visible = [item for item in visible if item.category == category]
        if favorite is not None:
            visible = [item for item in visible if item.is_favorite is favorite]
        if search:
            term = search.lower()
            visible = [
                item
                for item in visible
                if term in item.name.lower()
                or term in (item.description or "").lower()
                or term in item.content.lower()
            ]
        if not include_inactive:
            visible = [item for item in visible if item.is_active]
        return visible[offset : offset + limit]

    def get_by_id(self, template_id):
        return self.items.get(template_id)

    def update(self, template, data: PromptTemplateUpdate):
        values = data.model_dump(exclude_unset=True)
        if "metadata" in values:
            values["metadata_"] = values.pop("metadata")
        for field, value in values.items():
            setattr(template, field, value)
        return template

    def archive(self, template):
        template.is_active = False
        return template


def make_user(role: UserRole = UserRole.MEMBER):
    return SimpleNamespace(id=uuid4(), role=role)


def make_payload(**overrides):
    values = {
        "name": "Resumo técnico",
        "description": "Resume documentos técnicos.",
        "category": "documentation",
        "content": "Resuma {{document}} para o projeto {{project}}.",
        "variables": ["document", "project"],
        "is_public": False,
        "is_favorite": False,
        "is_active": True,
        "metadata": {"source": "test"},
    }
    values.update(overrides)
    return PromptTemplateCreate(**values)


def test_member_can_create_private_template() -> None:
    repository = FakePromptTemplateRepository()
    service = PromptTemplateService(repository)
    user = make_user()

    template = service.create(make_payload(), user)

    assert template.owner_id == user.id
    assert template.name == "Resumo técnico"
    assert template.variables == ["document", "project"]
    assert template.metadata_ == {"source": "test"}


def test_member_cannot_create_public_template() -> None:
    service = PromptTemplateService(FakePromptTemplateRepository())

    with pytest.raises(HTTPException) as exc_info:
        service.create(make_payload(is_public=True), make_user())

    assert exc_info.value.status_code == 403


def test_admin_can_create_public_template() -> None:
    repository = FakePromptTemplateRepository()
    service = PromptTemplateService(repository)
    admin = make_user(UserRole.ADMIN)

    template = service.create(make_payload(is_public=True), admin)

    assert template.is_public is True


def test_list_applies_visibility_project_category_favorite_and_search_filters() -> None:
    repository = FakePromptTemplateRepository()
    service = PromptTemplateService(repository)
    owner = make_user()
    other = make_user()
    project_id = uuid4()

    expected = service.create(
        make_payload(project_id=project_id, is_favorite=True, name="Gerar casos de teste"),
        owner,
    )
    service.create(make_payload(project_id=uuid4(), name="Outro projeto"), owner)
    service.create(make_payload(project_id=project_id, category="general", name="Outra categoria"), owner)
    service.create(make_payload(project_id=project_id, name="Privado de outro usuário"), other)
    service.create(make_payload(project_id=None, name="Público global", is_public=True), make_user(UserRole.ADMIN))

    result = service.list(
        user=owner,
        project_id=project_id,
        category="documentation",
        favorite=True,
        search="casos",
    )

    assert result == [expected]


def test_private_template_is_hidden_from_other_user() -> None:
    repository = FakePromptTemplateRepository()
    service = PromptTemplateService(repository)
    owner = make_user()
    other = make_user()
    template = service.create(make_payload(), owner)

    with pytest.raises(HTTPException) as exc_info:
        service.get(template.id, other)

    assert exc_info.value.status_code == 404


def test_public_template_is_visible_to_other_user() -> None:
    repository = FakePromptTemplateRepository()
    service = PromptTemplateService(repository)
    admin = make_user(UserRole.ADMIN)
    other = make_user()
    template = service.create(make_payload(is_public=True), admin)

    assert service.get(template.id, other) is template


def test_non_owner_cannot_update_or_archive_private_template() -> None:
    repository = FakePromptTemplateRepository()
    service = PromptTemplateService(repository)
    owner = make_user()
    other = make_user()
    template = service.create(make_payload(), owner)

    with pytest.raises(HTTPException) as update_error:
        service.update(template.id, PromptTemplateUpdate(name="Novo nome"), other)
    with pytest.raises(HTTPException) as archive_error:
        service.archive(template.id, other)

    assert update_error.value.status_code == 404
    assert archive_error.value.status_code == 404


def test_owner_can_update_and_archive_template() -> None:
    repository = FakePromptTemplateRepository()
    service = PromptTemplateService(repository)
    owner = make_user()
    template = service.create(make_payload(), owner)

    updated = service.update(
        template.id,
        PromptTemplateUpdate(
            name="Template atualizado",
            is_favorite=True,
            variables=["selection"],
            metadata={"version": 2},
        ),
        owner,
    )
    archived = service.archive(template.id, owner)

    assert updated.name == "Template atualizado"
    assert updated.is_favorite is True
    assert updated.variables == ["selection"]
    assert updated.metadata_ == {"version": 2}
    assert archived.is_active is False


def test_only_admin_can_publish_existing_template() -> None:
    repository = FakePromptTemplateRepository()
    service = PromptTemplateService(repository)
    owner = make_user()
    template = service.create(make_payload(), owner)

    with pytest.raises(HTTPException) as exc_info:
        service.update(template.id, PromptTemplateUpdate(is_public=True), owner)

    assert exc_info.value.status_code == 403


def test_admin_can_manage_any_template_and_include_inactive() -> None:
    repository = FakePromptTemplateRepository()
    service = PromptTemplateService(repository)
    owner = make_user()
    admin = make_user(UserRole.ADMIN)
    template = service.create(make_payload(), owner)
    service.archive(template.id, owner)

    updated = service.update(template.id, PromptTemplateUpdate(is_public=True), admin)
    result = service.list(user=admin, include_inactive=True)

    assert updated.is_public is True
    assert template in result


def test_variables_are_trimmed_and_deduplicated() -> None:
    payload = make_payload(variables=[" document ", "project", "document", ""])

    assert payload.variables == ["document", "project"]
