# Prompt — Implementação do Frontend (Next.js)

---

Preciso que você implemente o frontend completo do **SmartDocs**, um sistema de gestão de documentos inteligente com chat SQL, usando **Next.js (App Router) + TypeScript + TailwindCSS + Shadcn/UI**.

## Contexto

O sistema é um SaaS interno onde usuários fazem upload de documentos, visualizam dados extraídos por IA, conversam com seus documentos via chat em linguagem natural, e admins gerenciam usuários. O backend é uma API FastAPI já implementada.

## Documentos de referência no projeto

- **`docs/telas-frontend.md`** — Mockups das 5 telas (Login, Chat, Upload, Documentos, Admin) gerados no Stitch com tema dark navy e estética corporativa profissional
- **`docs/rotas-backend.md`** — 13 endpoints da API com request/response JSON detalhados — usar como contrato de integração

Siga esses documentos como spec. Os mockups definem a estética. As rotas definem a integração.

## Stack

- **Next.js 14+** com App Router
- **TypeScript** strict
- **TailwindCSS** para estilização
- **Shadcn/UI** como biblioteca de componentes
- **Axios ou fetch** para chamadas à API
- Autenticação via **JWT** armazenado em cookie httpOnly ou localStorage

## O que implementar

### 1. Setup do projeto
- Next.js com App Router + TypeScript + TailwindCSS
- Instalar Shadcn/UI com tema dark
- Configurar cores: fundo navy/slate (#0F172A), acento azul (#136dec), fonte Inter
- Criar layout base com sidebar de navegação (Dashboard, Chat, Upload, Documentos, Administração)

### 2. Tela: Login (`/login`)
- Conforme mockup em `docs/telas-frontend.md` — seção 1
- Card centralizado com glassmorphism sutil
- Campos: email, senha. Botão "Entrar"
- Integrar com `POST /auth/login` conforme `docs/rotas-backend.md`
- Após login, salvar token e redirecionar para `/documents`
- Sem link de cadastro (admins criam contas)

### 3. Tela: Chat (`/chat`)
- Conforme mockup em `docs/telas-frontend.md` — seção 2
- Interface estilo ChatGPT: mensagens do usuário à direita (azul), respostas da IA à esquerda (card escuro)
- Respostas podem conter **tabelas formatadas** e texto em markdown
- Input na parte inferior: "Pergunte algo sobre seus documentos..." + botão enviar
- Integrar com `POST /chat` conforme `docs/rotas-backend.md`
- Mostrar loading/typing indicator enquanto aguarda resposta
- Opcional: carregar histórico com `GET /chat/history`

### 4. Tela: Upload (`/upload`)
- Conforme mockup em `docs/telas-frontend.md` — seção 3
- Dropzone drag-and-drop com ícone de cloud, formatos suportados listados
- Aceitar: PDF, DOCX, XLSX, PPTX, JPG, PNG
- Upload múltiplo de arquivos
- Lista de uploads recentes com: nome do arquivo, tamanho, barra de progresso, status (✅ concluído, 🔄 processando, ❌ falhou)
- Botão "Reprocessar" em itens com falha → `POST /documents/{id}/reprocess`
- Integrar com `POST /documents/upload` conforme `docs/rotas-backend.md`

### 5. Tela: Documentos (`/documents`)
- Conforme mockup em `docs/telas-frontend.md` — seção 4
- Grid/tabela com colunas: Nome, Tipo (badges coloridos), Data Upload, Páginas, Status (badges: verde/amarelo/vermelho)
- Barra de filtros: campo busca por nome + dropdown de status + contador total
- Paginação
- Linha expandível ao clicar: mostra preview do documento (iframe/embed do PDF) à esquerda e dados extraídos organizados (key-value pairs + tabelas) à direita
- Botões na linha expandida: "Ver Documento Completo" e "Reprocessar"
- Integrar com `GET /documents` e `GET /documents/{id}` conforme `docs/rotas-backend.md`
- Visualização do arquivo via `GET /documents/{id}/file`

### 6. Tela: Admin (`/admin/users`) — somente admins
- Conforme mockup em `docs/telas-frontend.md` — seção 5
- Tabela de usuários: Nome, Email, Perfil (badge azul Admin / cinza Usuário), Data Cadastro, Ações (editar, deletar)
- Botão "+ Novo Usuário" abre modal com: Nome, Email, Senha, Perfil (Admin/Usuário)
- Editar usuário: mesma modal preenchida
- Deletar: confirmação antes de remover
- Integrar com `GET/POST/PUT/DELETE /admin/users` conforme `docs/rotas-backend.md`
- Esconder link "Administração" na sidebar para usuários com `role=user`

### 7. Infraestrutura do front
- AuthContext/Provider: gerenciar estado de autenticação, token, dados do usuário
- Middleware ou guard: redirecionar para `/login` se não autenticado
- Guard de admin: redirecionar para `/documents` se tentar acessar `/admin` sem ser admin
- API client centralizado (axios instance) com interceptor de token e tratamento de 401
- Componentes reutilizáveis: Sidebar, PageHeader, StatusBadge, DataTable

## Regras de design

- **Tema dark obrigatório** — fundo #0F172A, cards com bordas sutis, texto branco/cinza
- **Acento azul #136dec** para botões primários, links ativos, badges
- **Sem estética infantil**: visual corporativo, sério, premium
- **Responsivo**: funcionar bem em desktop (foco principal) e tablet
- **Tipografia**: Inter do Google Fonts
- **Componentes Shadcn**: Card, Button, Badge, Table, Dialog, Toast, Tabs, DropdownMenu, Input, Select
- **Micro-animações**: hover suave em cards/botões, transições de página, skeleton loading

## Resultado esperado

O frontend deve rodar com `npm run dev`, conectar na API backend (variável de ambiente `NEXT_PUBLIC_API_URL`), e todas as 5 telas devem funcionar conforme os mockups e os payloads da API.
