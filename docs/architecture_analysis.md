# SmartDocs: Análise Arquitetural End-to-End

Esta documentação consolida a visão arquitetural do projeto SmartDocs, listando seus pontos fortes tecnológicos, potenciais gargalos e estratégias práticas de melhoria e escalabilidade.

## 🏗️ Visão Arquitetural (End-to-End)

### 1. Frontend (Interface e Interação)
* **Stack**: Next.js 16, React 19, Tailwind CSS v4.
* **UI/UX**: Integração com Shadcn UI, Radix UI e Lucide React, promovendo uma base de componentes flexível, limpa e altamente customizável.
* **Visualização de Dados**: Uso de `@tanstack/react-table` para renderização de tabelas e dataframes dinâmicos gerados pelo agente. `react-markdown` para formatação das respostas da IA.

### 2. Backend (Core e APIs)
* **Stack**: FastAPI com arquitetura fortemente assíncrona.
* **Banco de Dados**: PostgreSQL com `asyncpg` e `SQLAlchemy 2.0`.
* **Segurança**: Autenticação nativa baseada em JWT com hashing seguro usando `pwdlib[argon2]`.
* **Integração de Arquivos e Nuvem**: Azure AI Document Intelligence para extração de conteúdo estruturado, e Azure Blob Storage para o armazenamento físico e escalável dos anexos.

### 3. Inteligência Artificial (Agentic AI)
* **Orquestração**: Baseado em LangChain e LangGraph, estruturando fluxos de chat multicamadas que misturam geração de texto com chamadas de banco de dados (`database_query tool`).
* **Busca Semântica (RAG)**: Armazenamento vetorial via extensão `pgvector` nativa no PostgreSQL, mantendo embeddings perfeitamente integrados ao banco relacional.

---

## ⚠️ Potenciais Gargalos e Riscos

1. **Processamento Síncrono de Extratos Longos (Azure AI)**
   * **Risco**: Hoje a chamada para o Azure Document Intelligence ocorre no fluxo da requisição HTTP local (FastAPI). Documentos com dezenas de páginas causarão *timeouts* na API, sobrecarga nos workers Uvicorn e paralisação infinita na UI para o usuário final.

2. **Segurança e Escopo do Agente SQL (Database Query Tool)**
   * **Risco**: Se o agente possuir acesso irrestrito ao *schema* ou usar uma *connection string* com permissões de gravação, eventuais alucinações (ex: confusão devido a colunas removidas, como `document_type`) podem vazar dados indesejados ou até rodar queries pesadas que afetem a performance do banco.

3. **Performance da Busca no RAG: Vetorial vs. Exata**
   * **Risco**: `pgvector` e buscas em embeddings (busca semântica) perdem muita precisão quando o usuário demanda buscas exatas, como ids de documentos ("contrato 12345") ou valores nominais absolutos.

4. **Inchaço de Contexto (*Context Window* do LLM)**
   * **Risco**: A interface agora renderiza *DataTables* complexas geradas como parte do envio das respostas. Se esses *datasets* brutos forem re-enviados nas mensagens consecutivas do histórico (memória do LangGraph), o custo financeiro da OpenAI subirá drasticamente e novos limites de *tokens* serão estourados muito rapidamente.

---

## 💡 Estratégias de Melhoria e Evolução

1. **Processamento Assíncrono via Workers/Filas (Background Tasks)**
   * **Solução**: Isolar a extração via Azure. O upload no backend gera apenas uma *Task* e guarda o PDF no Azure Blob Storage com status "Processando". Filas (via Celery, Redis ou tabelas próprias no PostgreSQL) acionam o script em segundo plano sem prender o FastAPI, e notificam a UI ao concluir (via WebSockets ou *Polling*).

2. **Injeção de Contexto Limitada para o Agente ("Schema Trimming")**
   * **Solução**: Restringir drasticamente o schema de tabelas visível no prompt de sistema das *Database Tools*. Ocultar colunas irrelevantes à busca (como `updated_at`, `password_hash`, IDs sistêmicos). Prover apenas as chaves necessárias relacionais.

3. **Busca Híbrida (Hybrid Search Engine)**
   * **Solução**: Mesclar as buscas vetoriais (`pgvector`) com algoritmos Léxicos baseados em palavra-chave exata (Full-Text Search do PostgreSQL ou BM25 do Elastic/Meili). O AI cruzará os dois índices garantindo os melhores "conceitos" e os "ids/nomes" simultaneamente.

4. **Resumo Automático de Memória (Paginação de Histórico AI)**
   * **Solução**: Enviar tabelas preenchidas pro LLM apenas na próxima mensgem. Para interações antigas, varrer a variável do Histórico substituindo os JSON longos por respostas encurtadas na memória do chat. Ex: `[O sistema retornou uma tabela com N linhas contendo o relatório solicitado]`.

5. **Observabilidade e Monitoramento de IA (LLM Tracing)**
   * **Solução**: Adicionar integrações aos *callbacks* do LangChain (ex: LangSmith ou Phoenix). Auxilia enormemente na correção de bugs dos Prompts exibindo em uma UI o que o LLM "pensou", ferramentas executadas, os dados pesquisados, e falhas de raciocínio.
