# 🔌 Rotas do Backend — SmartDocs API

Todas as rotas FastAPI mapeadas para as telas do frontend.

---

## Autenticação

> Tela: **Login**

### `POST /auth/login`
Login do usuário. Retorna JWT.

```json
// Request
{
  "email": "user@empresa.com",
  "password": "senha123"
}

// Response 200
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "name": "Tiago Silva",
    "email": "user@empresa.com",
    "role": "admin"
  }
}

// Response 401
{ "detail": "Email ou senha inválidos" }
```

### `GET /auth/me`
Retorna dados do usuário logado (usado pelo front ao carregar a app).

```json
// Headers: Authorization: Bearer <token>

// Response 200
{
  "id": 1,
  "name": "Tiago Silva",
  "email": "user@empresa.com",
  "role": "admin"
}
```

---

## Documentos — Upload

> Tela: **Upload de Documentos**

### `POST /documents/upload`
Upload de um ou mais arquivos. Salva no Blob e inicia processamento em background.

```
Content-Type: multipart/form-data
Field: files (múltiplos arquivos)
Headers: Authorization: Bearer <token>
```

```json
// Response 202
{
  "documents": [
    {
      "id": 1,
      "filename": "Contrato_Prestacao.pdf",
      "status": "uploaded",
      "created_at": "2025-03-01T10:00:00Z"
    },
    {
      "id": 2,
      "filename": "Relatorio_Q3.xlsx",
      "status": "uploaded",
      "created_at": "2025-03-01T10:00:00Z"
    }
  ]
}
```

### `POST /documents/{id}/reprocess`
Reprocessa um documento que falhou. Pega o arquivo do Blob e roda extração novamente.

```json
// Response 202
{
  "id": 1,
  "status": "processing",
  "message": "Reprocessamento iniciado"
}

// Response 404
{ "detail": "Documento não encontrado" }

// Response 409
{ "detail": "Documento já está sendo processado" }
```

---

## Documentos — Listagem e Detalhes

> Tela: **Documentos (Grid + Detalhes)**

### `GET /documents`
Lista documentos do usuário com filtros e paginação.

```
Query params:
  ?search=contrato         (busca por nome do arquivo)
  &status=processed        (uploaded | processing | processed | failed)
  &page=1
  &per_page=20

Headers: Authorization: Bearer <token>
```

```json
// Response 200
{
  "documents": [
    {
      "id": 1,
      "filename": "Contrato_ABC.pdf",
      "original_extension": "pdf",
      "type": "contrato",
      "upload_date": "2025-03-01T10:00:00Z",
      "page_count": 5,
      "status": "processed"
    }
  ],
  "total": 47,
  "page": 1,
  "per_page": 20,
  "total_pages": 3
}
```

### `GET /documents/{id}`
Detalhes completos de um documento (usado ao expandir a linha no grid).

```json
// Response 200
{
  "id": 1,
  "filename": "Contrato_ABC.pdf",
  "original_extension": "pdf",
  "mime_type": "application/pdf",
  "type": "contrato",
  "upload_date": "2025-03-01T10:00:00Z",
  "page_count": 5,
  "status": "processed",
  "blob_url": "https://smartdocs.blob.core.windows.net/documents/abc123.pdf",
  "extracted_text": "CONTRATO DE PRESTAÇÃO DE SERVIÇOS...",
  "fields": [
    {
      "field_key": "Cliente",
      "field_value": "Empresa ABC",
      "confidence": 0.97,
      "page_number": 1
    },
    {
      "field_key": "Valor",
      "field_value": "R$ 45.000,00",
      "confidence": 0.95,
      "page_number": 1
    },
    {
      "field_key": "Data Início",
      "field_value": "01/03/2025",
      "confidence": 0.99,
      "page_number": 1
    }
  ],
  "tables": [
    {
      "table_index": 0,
      "page_number": 2,
      "headers": ["Item", "Quantidade", "Valor Unitário", "Total"],
      "rows": [
        ["Consultoria", "40h", "R$ 500", "R$ 20.000"],
        ["Desenvolvimento", "80h", "R$ 300", "R$ 24.000"]
      ]
    }
  ],
  "error_message": null
}
```

### `GET /documents/{id}/file`
Retorna o arquivo original para visualização no front (proxy do Blob ou redirect).

```
Response: 302 Redirect → blob_url (com SAS token temporário)
  ou
Response: 200 com Content-Type do arquivo (stream direto)
```

---

## Chat

> Tela: **Chat com Documentos**

### `POST /chat`
Envia pergunta em linguagem natural, recebe resposta baseada nos dados do banco.

```json
// Request
{
  "question": "Quais contratos vencem nos próximos 30 dias?"
}

// Response 200
{
  "answer": "Encontrei 3 contratos que vencem nos próximos 30 dias:\n\n1. **Contrato ABC** — vence em 15/03/2025 — R$ 45.000\n2. **Contrato XYZ** — vence em 22/03/2025 — R$ 120.000\n3. **Contrato DEF** — vence em 28/03/2025 — R$ 18.500",
  "sql_used": "SELECT c.client_name, c.end_date, c.contract_value FROM contracts c JOIN documents d ON c.document_id = d.id WHERE d.user_id = 1 AND c.end_date BETWEEN NOW() AND NOW() + INTERVAL '30 days' ORDER BY c.end_date",
  "row_count": 3,
  "data": [
    {"client_name": "Empresa ABC", "end_date": "2025-03-15", "contract_value": 45000},
    {"client_name": "Empresa XYZ", "end_date": "2025-03-22", "contract_value": 120000},
    {"client_name": "Empresa DEF", "end_date": "2025-03-28", "contract_value": 18500}
  ]
}
```

### `GET /chat/history`
Histórico de conversas do usuário (opcional, para persistir conversas).

```json
// Query: ?limit=50

// Response 200
{
  "messages": [
    {
      "id": 1,
      "question": "Quais contratos vencem nos próximos 30 dias?",
      "answer": "Encontrei 3 contratos...",
      "created_at": "2025-03-01T14:30:00Z"
    }
  ]
}
```

---

## Administração de Usuários

> Tela: **Gerenciamento de Usuários** (somente `role=admin`)

### `GET /admin/users`
Lista todos os usuários cadastrados.

```json
// Response 200
{
  "users": [
    {
      "id": 1,
      "name": "Tiago Silva",
      "email": "tiago@empresa.com",
      "role": "admin",
      "created_at": "2025-01-15T10:00:00Z"
    },
    {
      "id": 2,
      "name": "Maria Santos",
      "email": "maria@empresa.com",
      "role": "user",
      "created_at": "2025-02-01T08:00:00Z"
    }
  ]
}
```

### `POST /admin/users`
Cadastra novo usuário (admin define email, nome, senha e role).

```json
// Request
{
  "name": "João Oliveira",
  "email": "joao@empresa.com",
  "password": "senha_forte_123",
  "role": "user"
}

// Response 201
{
  "id": 3,
  "name": "João Oliveira",
  "email": "joao@empresa.com",
  "role": "user",
  "created_at": "2025-03-01T10:00:00Z"
}

// Response 409
{ "detail": "Email já cadastrado" }
```

### `PUT /admin/users/{id}`
Atualiza dados de um usuário (nome, email, role, senha opcional).

```json
// Request
{
  "name": "João Oliveira",
  "email": "joao@empresa.com",
  "role": "admin",
  "password": null
}

// Response 200
{
  "id": 3,
  "name": "João Oliveira",
  "email": "joao@empresa.com",
  "role": "admin",
  "created_at": "2025-03-01T10:00:00Z"
}
```

### `DELETE /admin/users/{id}`
Remove um usuário. Não pode deletar a si mesmo.

```json
// Response 204 (No Content)

// Response 400
{ "detail": "Não é possível deletar seu próprio usuário" }
```

---

## Resumo de Rotas

| Método | Rota | Auth | Tela | Descrição |
|--------|------|------|------|-----------|
| `POST` | `/auth/login` | ❌ | Login | Autenticação |
| `GET` | `/auth/me` | ✅ | Todas | Usuário logado |
| `POST` | `/documents/upload` | ✅ | Upload | Upload de arquivos |
| `POST` | `/documents/{id}/reprocess` | ✅ | Upload / Docs | Reprocessar documento |
| `GET` | `/documents` | ✅ | Documentos | Listar com filtros |
| `GET` | `/documents/{id}` | ✅ | Documentos | Detalhes + dados extraídos |
| `GET` | `/documents/{id}/file` | ✅ | Documentos | Visualizar arquivo original |
| `POST` | `/chat` | ✅ | Chat | Pergunta → SQL → Resposta |
| `GET` | `/chat/history` | ✅ | Chat | Histórico de perguntas |
| `GET` | `/admin/users` | 🔒 admin | Admin | Listar usuários |
| `POST` | `/admin/users` | 🔒 admin | Admin | Criar usuário |
| `PUT` | `/admin/users/{id}` | 🔒 admin | Admin | Editar usuário |
| `DELETE` | `/admin/users/{id}` | 🔒 admin | Admin | Remover usuário |

**Total: 13 endpoints**
