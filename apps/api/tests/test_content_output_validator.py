from app.services.content_output_validator import ContentOutputValidator


def test_validator_accepts_complete_content() -> None:
    validator = ContentOutputValidator()
    content = """
    1. Ideia central
    Explicar guard-rails de forma simples.

    2. Três opções de gancho
    Opção 1: Sua IA pode sair do controle sem você perceber.
    Opção 2: O que impede um chatbot de responder qualquer coisa?
    Opção 3: Guard-rails são o freio de segurança da IA.

    3. Roteiro
    0–2s: "Você confiaria em uma IA sem freios?"
    2–8s: "Sem guard-rails, ela pode gerar conteúdo perigoso."
    8–15s: "Por exemplo, um filtro pode bloquear pedidos para expor dados pessoais."
    15–20s: "É assim que guard-rails protegem usuários e sistemas."

    4. Três opções de título
    Título 1: O freio de segurança da IA
    Título 2: Por que toda IA precisa de guard-rails
    Título 3: Como impedir respostas perigosas

    5. Legenda
    Guard-rails ajudam a manter sistemas de IA dentro de limites seguros.

    6. Hashtags
    #GuardRails #LLM #IA #Segurança #Tecnologia

    7. Chamada para ação
    Siga o canal para aprender IA na prática.
    """

    result = validator.validate(content)

    assert result.is_valid is True
    assert result.issues == ()


def test_validator_rejects_outline_placeholders_and_citations() -> None:
    validator = ContentOutputValidator()
    content = """
    Ideia central: explicar guard-rails.
    Gancho 1: falar sobre segurança.
    Gancho 2: mostrar como funciona.
    Gancho 3: apresentar um exemplo.
    Roteiro: começar com uma introdução, explicar o conceito e concluir com a importância.
    Título: Guard-rails para LLMs.
    Legenda: confira mais.
    Hashtags: #IA
    Chamada para ação: clique em [Insira o link aqui]. [Fonte 1]
    """

    result = validator.validate(content)

    assert result.is_valid is False
    assert any("falas completas" in issue for issue in result.issues)
    assert any("placeholders" in issue for issue in result.issues)
    assert any("citações indevidas" in issue for issue in result.issues)
    assert any("marcação de tempo" in issue for issue in result.issues)


def test_build_refinement_instructions_lists_detected_issues() -> None:
    validator = ContentOutputValidator()
    result = validator.validate("Ideia central: conteúdo incompleto")

    instructions = validator.build_refinement_instructions(result)

    assert "Reescreva a resposta" in instructions
    assert "Seção obrigatória ausente" in instructions
    assert "sem comentar o processo de revisão" in instructions
