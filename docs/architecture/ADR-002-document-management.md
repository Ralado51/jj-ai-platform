# ADR-002 — Gestão de documentos por projeto

## Status

Aceito — Sprint 2.

## Contexto

A JJ AI Platform precisa permitir que cada projeto receba arquivos que, em etapas futuras, serão processados para extração de texto, chunking, embeddings, busca vetorial e RAG.

O domínio já possui a entidade `Asset`, vinculada a `Project`, com suporte a arquivos, tipo, MIME type, tamanho, checksum, provedor e caminho de armazenamento. O enum `AssetType` já contém o valor `document`.

Criar uma segunda entidade `Document` nesta etapa duplicaria responsabilidades de armazenamento e metadados.

## Decisão

A Sprint 2 reutilizará `Asset` como registro persistente dos documentos, com `asset_type=document`.

Metadados específicos do processamento serão mantidos inicialmente em `asset_metadata`, com a seguinte estrutura prevista:

```json
{
  "processing_status": "uploaded",
  "original_filename": "arquivo.pdf",
  "extension": ".pdf",
  "uploaded_by": "user-uuid",
  "extraction": {
    "status": "pending",
    "error": null
  },
  "embedding": {
    "status": "pending",
    "model": null
  }
}
```

Status iniciais:

- `uploaded`: arquivo recebido e persistido;
- `processing`: reservado para extração futura;
- `ready`: reservado para documento processado;
- `failed`: falha de processamento;
- `archived`: remoção lógica.

## Armazenamento

Nesta sprint, os arquivos serão gravados em volume persistente fora do banco de dados.

Estrutura prevista:

```text
/data/jj-ai/documents/<project_id>/<asset_id>/<safe_filename>
```

O banco armazenará apenas metadados e o caminho interno. Caminhos absolutos não serão expostos pela API.

A abstração deverá permitir substituição futura por armazenamento compatível com S3 sem alterar o contrato público dos endpoints.

## Regras de segurança

- Todos os endpoints exigem JWT válido.
- O projeto deve existir e estar ativo.
- O nome do arquivo será normalizado antes da gravação.
- O caminho final será gerado pelo backend, nunca fornecido pelo cliente.
- Extensão e MIME type serão validados em conjunto.
- O tamanho máximo será configurável por variável de ambiente.
- O checksum SHA-256 será calculado durante o upload.
- Arquivos não serão armazenados no PostgreSQL.
- A exclusão deverá evitar path traversal e remoção fora do diretório autorizado.

## Tipos inicialmente aceitos

- PDF
- DOCX
- TXT
- Markdown
- CSV
- XLSX
- PNG
- JPEG

Imagens serão aceitas como documentos de conhecimento, mas OCR não faz parte da Sprint 2.

## Contrato inicial da API

```text
POST   /api/v1/projects/{project_id}/documents
GET    /api/v1/projects/{project_id}/documents
GET    /api/v1/projects/{project_id}/documents/{document_id}
DELETE /api/v1/projects/{project_id}/documents/{document_id}
```

O identificador público do documento corresponderá ao `id` do `Asset`.

## Permissões

- `admin`: upload, listagem, consulta e exclusão;
- `member`: upload, listagem e consulta;
- `viewer`: listagem e consulta;
- exclusão por `member` poderá ser adicionada posteriormente caso exista propriedade explícita do documento.

## Fora do escopo da Sprint 2

- Extração de texto;
- OCR;
- chunking;
- embeddings;
- busca vetorial;
- chat RAG;
- antivírus externo;
- versionamento de documentos;
- compartilhamento público.

## Consequências

### Positivas

- Reutiliza o modelo de arquivos existente.
- Evita duplicação entre documentos, vídeos, imagens e artefatos.
- Mantém a arquitetura preparada para o Creator OS.
- Permite evoluir para S3 e processamento assíncrono.

### Pontos de atenção

- `asset_metadata` precisa ser validado no serviço para evitar estrutura inconsistente.
- Caso o domínio de documentos cresça significativamente, uma tabela especializada poderá ser introduzida posteriormente, mantendo `Asset` como registro físico do arquivo.
