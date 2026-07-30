"""seed content creator prompt templates

Revision ID: 20260730_03
Revises: 20260730_02
Create Date: 2026-07-30 18:58:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260730_03"
down_revision = "20260730_02"
branch_labels = None
depends_on = None

TEMPLATE_IDS = [
    "8a9b8ec2-09db-4de0-9d76-3769be92c4b0",
    "c4ff8afb-bfb3-492f-a640-45d7ecf1c753",
    "5e918da1-15b3-44e4-adf8-d65408843e45",
    "f41898f4-b2da-4778-8c9e-66bca6740386",
    "7a97273d-cb21-41f7-9f6f-436b61d45dde",
    "d9701300-3142-4734-9bc5-72c646dd995d",
]


def upgrade() -> None:
    prompt_templates = sa.table(
        "prompt_templates",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("project_id", postgresql.UUID(as_uuid=True)),
        sa.column("owner_id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("category", sa.String()),
        sa.column("content", sa.Text()),
        sa.column("variables", sa.JSON()),
        sa.column("is_public", sa.Boolean()),
        sa.column("is_favorite", sa.Boolean()),
        sa.column("is_active", sa.Boolean()),
        sa.column("metadata", sa.JSON()),
    )

    op.bulk_insert(
        prompt_templates,
        [
            {
                "id": TEMPLATE_IDS[0],
                "project_id": None,
                "owner_id": None,
                "name": "Roteiro para vídeo curto",
                "description": "Cria um roteiro objetivo e envolvente para Reels, Shorts ou TikTok.",
                "category": "Criador de conteúdo",
                "content": """Você é um estrategista de conteúdo para vídeos curtos.\n\nCrie um roteiro para um vídeo de {{duracao}} segundos sobre {{tema}}, direcionado a {{publico}}.\n\nEstruture a resposta em:\n1. Gancho de até 3 segundos;\n2. Desenvolvimento em frases curtas;\n3. Demonstração, exemplo ou prova;\n4. Chamada para ação;\n5. Sugestão de texto na tela.\n\nUse tom {{tom}} e linguagem natural. Evite introduções genéricas e comece com a parte mais interessante.""",
                "variables": ["duracao", "tema", "publico", "tom"],
                "is_public": True,
                "is_favorite": False,
                "is_active": True,
                "metadata": {"domain": "content-creator", "format": "short-video", "platforms": ["instagram", "youtube", "tiktok"]},
            },
            {
                "id": TEMPLATE_IDS[1],
                "project_id": None,
                "owner_id": None,
                "name": "Ideias de conteúdo",
                "description": "Gera ideias relevantes organizadas por objetivo e formato.",
                "category": "Criador de conteúdo",
                "content": """Atue como estrategista de conteúdo.\n\nGere {{quantidade}} ideias de conteúdo sobre {{nicho}} para {{plataforma}}, voltadas a {{publico}}.\n\nDistribua as ideias entre:\n- educação;\n- entretenimento;\n- autoridade;\n- relacionamento;\n- conversão.\n\nPara cada ideia, informe:\n1. título ou gancho;\n2. formato recomendado;\n3. mensagem principal;\n4. chamada para ação;\n5. nível de esforço: baixo, médio ou alto.\n\nEvite ideias repetitivas ou genéricas.""",
                "variables": ["quantidade", "nicho", "plataforma", "publico"],
                "is_public": True,
                "is_favorite": False,
                "is_active": True,
                "metadata": {"domain": "content-creator", "format": "ideation"},
            },
            {
                "id": TEMPLATE_IDS[2],
                "project_id": None,
                "owner_id": None,
                "name": "Legenda para redes sociais",
                "description": "Produz legendas com gancho, contexto, CTA e hashtags relevantes.",
                "category": "Criador de conteúdo",
                "content": """Crie uma legenda para {{plataforma}} sobre {{tema}}.\n\nPúblico: {{publico}}\nTom: {{tom}}\nObjetivo: {{objetivo}}\n\nA legenda deve conter:\n- primeira linha com forte gancho;\n- desenvolvimento claro e escaneável;\n- chamada para ação coerente;\n- até 5 hashtags específicas e relevantes.\n\nNão use clichês, excesso de emojis ou hashtags genéricas.""",
                "variables": ["plataforma", "tema", "publico", "tom", "objetivo"],
                "is_public": True,
                "is_favorite": False,
                "is_active": True,
                "metadata": {"domain": "content-creator", "format": "caption"},
            },
            {
                "id": TEMPLATE_IDS[3],
                "project_id": None,
                "owner_id": None,
                "name": "Calendário editorial semanal",
                "description": "Monta um plano semanal equilibrado de publicações.",
                "category": "Criador de conteúdo",
                "content": """Crie um calendário editorial de 7 dias para o nicho {{nicho}}, na plataforma {{plataforma}}, direcionado a {{publico}}.\n\nObjetivo principal: {{objetivo}}\nFrequência disponível: {{frequencia}}\n\nPara cada publicação, informe:\n1. dia;\n2. tema;\n3. formato;\n4. gancho;\n5. resumo do conteúdo;\n6. CTA;\n7. ativo necessário para produção.\n\nEquilibre conteúdos de alcance, relacionamento, autoridade e conversão.""",
                "variables": ["nicho", "plataforma", "publico", "objetivo", "frequencia"],
                "is_public": True,
                "is_favorite": False,
                "is_active": True,
                "metadata": {"domain": "content-creator", "format": "editorial-calendar"},
            },
            {
                "id": TEMPLATE_IDS[4],
                "project_id": None,
                "owner_id": None,
                "name": "Transformar conteúdo longo em cortes",
                "description": "Extrai ideias de cortes e adapta trechos para vídeos curtos.",
                "category": "Criador de conteúdo",
                "content": """Analise o conteúdo abaixo e identifique os melhores trechos para vídeos curtos:\n\n{{conteudo}}\n\nPara cada corte sugerido, entregue:\n1. título;\n2. gancho inicial;\n3. trecho ou ideia central;\n4. duração estimada;\n5. motivo pelo qual pode reter audiência;\n6. texto de apoio na tela;\n7. CTA sugerido.\n\nPriorize trechos com surpresa, utilidade, emoção, opinião forte ou transformação clara.""",
                "variables": ["conteudo"],
                "is_public": True,
                "is_favorite": False,
                "is_active": True,
                "metadata": {"domain": "content-creator", "format": "content-repurposing"},
            },
            {
                "id": TEMPLATE_IDS[5],
                "project_id": None,
                "owner_id": None,
                "name": "Analisar e melhorar conteúdo",
                "description": "Avalia um roteiro ou publicação e propõe uma versão mais forte.",
                "category": "Criador de conteúdo",
                "content": """Analise o conteúdo abaixo como um editor especializado em retenção e clareza:\n\n{{conteudo}}\n\nAvalie de 0 a 10:\n- força do gancho;\n- clareza;\n- ritmo;\n- valor para o público;\n- originalidade;\n- chamada para ação.\n\nDepois entregue:\n1. principais problemas;\n2. trechos que devem ser removidos ou encurtados;\n3. oportunidades de melhoria;\n4. uma versão reescrita e mais eficaz;\n5. três opções alternativas de gancho.""",
                "variables": ["conteudo"],
                "is_public": True,
                "is_favorite": False,
                "is_active": True,
                "metadata": {"domain": "content-creator", "format": "content-review"},
            },
        ],
    )


def downgrade() -> None:
    prompt_templates = sa.table(
        "prompt_templates",
        sa.column("id", postgresql.UUID(as_uuid=True)),
    )
    op.execute(
        prompt_templates.delete().where(prompt_templates.c.id.in_(TEMPLATE_IDS))
    )
