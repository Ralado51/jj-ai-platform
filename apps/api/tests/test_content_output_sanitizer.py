from app.services.content_output_sanitizer import ContentOutputSanitizer
from app.services.content_output_validator import ContentOutputValidator


def test_sanitizer_removes_rag_leakage_and_meta_commentary() -> None:
    content = """
### 7. Chamada Para Ação Final
Conheça nossos guard-rails e comece a proteger hoje! [Fonte 1]

Essa resposta segue rigorosamente as regras e foi adaptada ao formato solicitado.
"""

    sanitized = ContentOutputSanitizer.sanitize(content)

    assert "[Fonte 1]" not in sanitized
    assert "Essa resposta segue" not in sanitized
    assert "nossos guard-rails" not in sanitized
    assert "saiba como implementar guard-rails" in sanitized


def test_validator_rejects_titles_that_repeat_hooks() -> None:
    content = """
### 1. Ideia Central
Explicar guard-rails em IA.

### 2. Opções de Gancho
Gancho 1: Guard-rails LLMs: proteja seus modelos
Gancho 2: LLMs seguros com guard-rails
Gancho 3: Como evitar ataques em seus modelos

### 3. Roteiro Completo
0-5s: "Sua IA pode responder fora das regras."
6-12s: "Por exemplo, um filtro bloqueia instruções perigosas."
13-20s: "A solução são guard-rails aplicados antes da resposta."

### 4. Títulos
Título 1: Guard-rails LLMs: proteja seus modelos
Título 2: LLMs seguros com guard-rails
Título 3: Como evitar ataques em seus modelos

### 5. Legenda
Proteja seus modelos com controles claros.

### 6. Hashtags
#IA #Guardrails

### 7. Chamada para Ação
Comente para receber mais exemplos.
"""

    result = ContentOutputValidator().validate(content)

    assert result.is_valid is False
    assert any("não devem repetir os ganchos" in issue for issue in result.issues)


def test_validator_rejects_meta_and_unsupported_offer() -> None:
    content = """
### 1. Ideia Central
Explicar guard-rails em IA.
### 2. Opções de Gancho
Gancho 1: Como proteger uma IA?
Gancho 2: O erro que deixa um chatbot vulnerável
Gancho 3: Por que sua IA precisa de limites?
### 3. Roteiro Completo
0-5s: "Sua IA pode sair das regras."
6-12s: "Por exemplo, um filtro bloqueia uma instrução maliciosa."
13-20s: "Guard-rails reduzem esse risco."
### 4. Títulos
Título 1: O freio de segurança da IA
Título 2: Como impedir respostas perigosas
Título 3: Limites que protegem chatbots
### 5. Legenda
Guard-rails ajudam a reduzir riscos.
### 6. Hashtags
#IA #Seguranca
### 7. Chamada para Ação
Conheça nossos guard-rails.

Essa resposta segue rigorosamente as regras.
"""

    result = ContentOutputValidator().validate(content)

    assert result.is_valid is False
    assert any("comentários do modelo" in issue for issue in result.issues)
    assert any("produto, serviço" in issue for issue in result.issues)
