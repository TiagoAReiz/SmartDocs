<div align="center">
  <img src="https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/file-text.svg" width="80" alt="SmartDocs Logo">
  
  # SmartDocs 🧠📄
  **An End-to-End Intelligent Document Platform**
  
  Uma plataforma moderna e altamente escalável capaz de extrair, armazenar e analisar documentos não-estruturados, combinando-os com uma gestão relacional e vetorial de ponta a ponta. Guiada por um sistema interativo de **Agentic AI**.
  
  <br />

  [![Next.js](https://img.shields.io/badge/Next.js-16-black?style=flat&logo=next.js)](https://nextjs.org/)
  [![React](https://img.shields.io/badge/React-19-blue?style=flat&logo=react)](https://react.dev/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-10.x-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
  [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791?style=flat&logo=postgresql)](https://www.postgresql.org/)
  [![LangChain](https://img.shields.io/badge/LangChain-LangGraph-yellow?style=flat)](https://www.langchain.com/)
  [![Azure](https://img.shields.io/badge/Microsoft_Azure-blue?style=flat&logo=microsoftazure)](https://azure.microsoft.com/)
  
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
2. **Python** (v3.10+) 
3. **PostgreSQL 15+** com a extensão `pgvector` instalada.
4. Contas na nuvem garantindo credenciais (*Azure Document Intelligence, Storage, LLM API Keys*).

### Subindo os Serviços

#### Passo 1. Subindo Backend e Banco de Dados
```bash
# Navegue a pasta do backend
cd backend

# Crie e habilite seu ambiente virtual (Linux/macOS)
python3 -m venv venv
source venv/bin/activate
# ou Windows: venv\Scripts\activate

# Instale as dependências API e LangChain Python
pip install -r requirements.txt

# Edite suas variáveis de autenticação em um `.env`
cp .env.example .env

# Aplique o schema das tabelas no PostgreSQL e rode o Uvicorn
alembic upgrade head
uvicorn app.main:app --reload
```
*(Opcional / Desejado: Também dispare em outro terminal o job worker executando o script `python worker_main.py` para testes de documentos grandes.)*

#### Passo 2. Subindo Frontend 
```bash
# Na pasta de frontend, instale suas dependências do Node
cd frontend
npm install

# Inicie o App em modo de desenvolvedor (Server-Side rendering ativado)
npm run dev
```

Abra a porta [http://localhost:3000](http://localhost:3000) no seu navegador para conversar com a aplicação!

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
