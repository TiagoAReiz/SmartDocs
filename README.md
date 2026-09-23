<div align="center">
  <img src="https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/file-text.svg" width="80" alt="SmartDocs Logo">
  
  # SmartDocs 🧠📄
  **An End-to-End Intelligent Document Platform**
  
  Uma plataforma moderna e altamente escalável capaz de extrair, armazenar e analisar documentos não-estruturados, combinando-os com uma gestão relacional e vetorial de ponta a ponta. Guiada por um sistema interativo de **Agentic AI**.
  
  <br />

  [![Next.js](https://img.shields.io/badge/Next.js-16-black?style=flat&logo=next.js)](https://nextjs.org/)
  [![React](https://img.shields.io/badge/React-19-blue?style=flat&logo=react)](https://react.dev/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
  [![PostgreSQL](https://img.shields.io/badge/PostgreSQL_17-pgvector-336791?style=flat&logo=postgresql)](https://www.postgresql.org/)
  [![LangChain](https://img.shields.io/badge/LangChain-LangGraph-yellow?style=flat)](https://www.langchain.com/)
  [![Azure](https://img.shields.io/badge/Microsoft_Azure-blue?style=flat&logo=microsoftazure)](https://azure.microsoft.com/)

  [![Backend CI](https://github.com/TiagoAReiz/SmartDocs/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/TiagoAReiz/SmartDocs/actions/workflows/backend-ci.yml)
  [![Frontend CI](https://github.com/TiagoAReiz/SmartDocs/actions/workflows/frontend-ci.yml/badge.svg)](https://github.com/TiagoAReiz/SmartDocs/actions/workflows/frontend-ci.yml)
  
</div>

---

## 🚀 O Projeto

O **SmartDocs** é mais do que  um simples pipeline de RAG (Retrieval-Augmented Generation). Ele introduz um **agente de Inteligência Artificial autônomo** capaz de raciocinar através de múltiplas etapas, cruzar dados estruturados escrevendo scripts *SQL* em tempo-real e interrogar a base de conhecimentos semântica – entregando respostas textuais profundas ou DataFrames (Tabelas e Gráficos) dinamicamente na Interface do usuário.

### ✨ Diferenciais e Funcionalidades

- **💬 Agentic Chat (LangGraph)**: Um agente orquestrador que compreende a intenção do usuário, planeja a execução e aciona as "tools" vitais, sejam elas para busca semântica em anexos ou resgates relacionais complexos.
- **📄 Processamento Assíncrono de Extratos**: Uso de workers/filas em background acoplados ao *Azure AI Document Intelligence* para extração otimizada do conteúdo de centenas de PDFs sem provocar lentidão no frontend ou *timeouts* da API.
- **🔍 Busca Híbrida Avançada (Semântica + Léxica)**: Combina o poder de análise de linguagem natural através da **busca semântica** (via *embeddings* nativos no PostgreSQL com `pgvector`) e a precisão técnica da **busca léxica** (ideal para palavras-chave exatas, nomenclaturas ou IDs). O Agente cruza inteligentemente os dados para garantir as melhores correspondências de texto ou contexto puro ao usuário.
- **🎨 UI e Visualização Riquíssima**: A nova *stack edge-ready* (React 19 + Next.js 16) usa bibliotecas modernas como Tailwind CSS v4, Shadcn e `@tanstack/react-table` para fornecer *data grids* nativos e flexíveis dentro do próprio histórico do Chat, sem sacrifícios de tempo de resposta.

---

## 🏗️ Arquitetura Sistêmica

### 🖥️ Frontend (Interface)
- **Framework:** Next.js 16 (App Router) + React 19.
- **Estilização / UI:** Tailwind CSS v4, Lucide React, componentes polidos por Radix UI e Shadcn UI.
- **Renderização Dinâmica:** `@tanstack/react-table` e `react-markdown` formatam retornos massivos originados através da IA, formatando tabelas brutas e textos ricos lindamente na UI.

### ⚙️ Backend (Core e APIs)
- **Framework e Assincronia:** FastAPI executando chamadas estritamente assíncronas usando Python Moderno.
- **Banco de Dados:** PostgreSQL com suporte via `asyncpg`, orquestração elegante de modelos e consultas em `SQLAlchemy 2.0` acoplado ao `Alembic` para o versionamento de _Migrations_.
- **Ecosistema de Nuvens:** Submissões são armazenadas escalavelmente no *Azure Blob Storage*.
- **Background Workers:** Estratégia de filas focadas em jobs pesados implementada puramente em python, poupando custo de deploy de novas tecnologias.

### 🧠 Inteligência Artificial (AI & Agentic Flow)
- O orquestrador usa o **LangGraph**, fornecendo ferramentas restritas *(Database Query Tools e Retrieval Tools)* ao prompt do LLM.
- Modelos poderosos gerando *embeddings* para vetorizações RAG otimizadas mantidas com segurança relacional e cruzadas semanticamente sob o guarda-chuva de modelos GPT (ex: *Azure OpenAI* / *OpenAI*).

---

## 🏃 Como Rodar Este Projeto Localmente

### Pré-requisitos Fundamentais
1. **Node.js** (v20+)
2. **Python** (3.12 — mesma versão usada no CI e no `Dockerfile`)
3. **Docker** (para subir PostgreSQL 17 + `pgvector` e o Azurite localmente) — ou um PostgreSQL próprio com a extensão `pgvector`.
4. Credenciais Azure (*Document Intelligence* e *Azure OpenAI*) para extração de documentos e chat. Sem elas a API sobe e autentica normalmente, mas upload/processamento e o agente não funcionam.

### Subindo os Serviços

#### Passo 1. Banco de Dados e Storage local
```bash
cd backend

# PostgreSQL 17 + pgvector (porta 5432) e Azurite (emulador do Blob Storage, porta 10000)
docker compose up -d db azurite
```

#### Passo 2. Backend (API + Worker)
```bash
# Ainda na pasta backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

# Variáveis de ambiente (os defaults já apontam para o docker compose acima;
# preencha AZURE_DI_* e AZURE_OPENAI_*)
cp .env.example .env

# Aplica o schema (inclui a extensão pgvector)
alembic upgrade head

# Cria o primeiro usuário admin (o login exige um usuário existente)
python -c "import asyncio; from app.database import async_session; from app.services.auth_service import create_user
async def main():
    async with async_session() as db:
        await create_user('Admin', 'admin@smartdocs.local', 'admin123', 'admin', db); await db.commit()
asyncio.run(main())"

# API em http://localhost:8000 (Swagger em /docs)
uvicorn app.main:app --reload
```
Em outro terminal (mesmo venv), suba o worker que processa os documentos enviados de forma assíncrona:
```bash
python worker_main.py
```

> Alternativa: `docker compose up --build` na pasta `backend` sobe banco, Azurite, API (roda as migrations no start) e worker de uma vez.

#### Passo 3. Frontend
```bash
cd frontend
npm install

# Opcional: a URL da API já tem default http://localhost:8000
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

npm run dev
```

Abra [http://localhost:3000](http://localhost:3000) e entre com `admin@smartdocs.local` / `admin123`.

### Testes e Qualidade
```bash
# Backend (com o banco do Passo 1 migrado)
cd backend && pip install ruff==0.16.8 && ruff check . && ruff format --check . && pytest tests/

# Frontend
cd frontend && npm run lint && npx tsc --noEmit && npm run build
```
Os mesmos passos rodam no GitHub Actions (`backend-ci.yml` e `frontend-ci.yml`) a cada push/PR na `main`.

---

## 🗺️ Roadmap Atual

A plataforma SmartDocs opera hoje num fluxo consistente de melhoria contínua visando maturidade completa nas abordagens RAG:
- [x] Extração isolada assíncrona escalável a documentos densos (Azure AI).
- [x] Interface gerando planilhas vivas (*Tanstack DataTables*).
- [x] Respostas mais assertivas e dinâmicas devido ao setup de Engine Híbrida de buscas da plataforma (*Busca Semântica Vectorial + Busca Léxica Relacional*).
- [ ] Escopo e Limitação do prompt via **Schema Trimming** p/ inibir querys perigosas pelo Agente.
- [ ] Estratégia de compactação semântica e paginação sobre o histórico de memória LangGraph para corte e proteção de custo de token no GPT.

---
> 💡 *Sinta-se livre para clonar, mandar _issues_ construtivos, pull-requests épicos ou inspirar-se nessa arquitetura.* Se o conceito lhe brilhar os olhos, não deixe de apoiar com uma **Star (⭐)** neste repositório.
