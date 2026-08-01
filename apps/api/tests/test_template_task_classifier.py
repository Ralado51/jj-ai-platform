from app.services.model_router import AITaskType
from app.services.template_task_classifier import TemplateTaskClassifier


def test_classifies_content_analysis_as_summarization() -> None:
    result = TemplateTaskClassifier().classify(
        name="Analisar um novo conteúdo",
        description="Extraia os principais pontos do material.",
    )

    assert result.task == AITaskType.SUMMARIZATION


def test_classifies_code_template() -> None:
    result = TemplateTaskClassifier().classify(
        name="Melhorar código Python",
        prompt="Refatore o código e explique o erro.",
    )

    assert result.task == AITaskType.CODING


def test_falls_back_to_general() -> None:
    result = TemplateTaskClassifier().classify(name="Assistente genérico")

    assert result.task == AITaskType.GENERAL
