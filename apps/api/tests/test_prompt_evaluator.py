from app.services.prompt_evaluator import PromptEvaluator


def test_evaluator_passes_strong_content() -> None:
    content = """
### 1. Ideia Central
Explicar como guard-rails evitam respostas perigosas em IA.

### 2. Opções de Gancho
Gancho 1: Você confiaria em uma IA que inventa regras?
Gancho 2: O erro que transforma um chatbot em risco para sua empresa
Gancho 3: Como impedir uma IA de responder qualquer coisa

### 3. Roteiro
0-4s: "Você confiaria em uma IA que inventa regras?"
5-9s: "O problema é que um chatbot sem limites pode responder fora da política."
10-14s: "Por exemplo, ele pode aprovar um reembolso que nunca existiu."
15-18s: "A consequência é prejuízo e perda de confiança."
19-23s: "A solução são guard-rails: regras que bloqueiam respostas inseguras."
24-27s: "Por isso, antes de publicar uma IA, teste seus limites."

### 4. Títulos
Título 1: O erro que faz uma IA inventar regras
Título 2: Como proteger seu chatbot antes do prejuízo
Título 3: Guard-rails: os freios de segurança da IA

### 5. Legenda
Seu chatbot precisa de limites antes de falar com clientes.

### 6. Hashtags
#IA #Guardrails #SegurançaDigital

### 7. Chamada para Ação
Comente "guard-rails" e compartilhe com seu time.
"""

    result = PromptEvaluator(minimum_score=8.0).evaluate(content)

    assert result.passed is True
    assert result.scores.overall >= 8.0
    assert result.scores.structure == 10.0
    assert result.strengths


def test_evaluator_flags_outline_and_repetition() -> None:
    content = """
Ideia central: falar sobre guard-rails.
Gancho 1: Guard-rails em IA
Gancho 2: Guard-rails em IA
Gancho 3: Guard-rails em IA
Roteiro: começar com uma introdução, explicar o conceito e concluir com a solução.
Título 1: Guard-rails em IA
Título 2: Guard-rails em IA
Título 3: Guard-rails em IA
Legenda: [Insira uma legenda]
Hashtags: #IA
Chamada para ação: Compartilhe.
[Fonte 1]
"""

    result = PromptEvaluator(minimum_score=8.0).evaluate(content)

    assert result.passed is False
    assert result.scores.overall < 8.0
    assert any("curiosidade" in issue for issue in result.issues)
    assert any("falas prontas" in issue for issue in result.issues)
    assert any("títulos" in issue for issue in result.issues)


def test_evaluator_rejects_empty_content() -> None:
    result = PromptEvaluator().evaluate("   ")

    assert result.passed is False
    assert result.scores.overall == 0
    assert result.issues == ("A resposta está vazia.",)


def test_evaluator_validates_minimum_score() -> None:
    for minimum_score in (-0.1, 10.1):
        try:
            PromptEvaluator(minimum_score=minimum_score)
        except ValueError as exc:
            assert "between 0 and 10" in str(exc)
        else:
            raise AssertionError("Expected ValueError")
