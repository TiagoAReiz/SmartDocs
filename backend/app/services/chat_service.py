"""
Chat service — LangChain agent with Azure OpenAI.

Uses a ReAct agent that decides autonomously when to query the database
versus responding directly (e.g. greetings, general questions).
"""

import json
from typing import Any, AsyncIterator
from uuid import UUID

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import AzureChatOpenAI
from langgraph.prebuilt import create_react_agent
from typing import Any, AsyncIterator, Callable, Optional
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.chat_message import ChatMessage
from app.services.tools import make_database_query_tool, make_get_schema_tool, _fetch_db_schema
from app.services.rag_tool import make_rag_search_tool


class OpenAIUnavailableError(RuntimeError):
    pass


SYSTEM_PROMPT = """Você é o SmartDocs Assistant, um assistente de gestão documental que responde EXCLUSIVAMENTE com base nos documentos armazenados no sistema.

## REGRA ABSOLUTA — FONTE ÚNICA DE VERDADE

⚠️ Você NÃO possui conhecimento próprio. NÃO use informações da internet, treinamento ou conhecimento geral.
⚠️ TODA resposta DEVE vir das ferramentas (database_query ou rag_search).
⚠️ Se não encontrar informação, diga: "Não encontrei essa informação nos documentos do sistema."
⚠️ NUNCA invente, suponha ou complemente com conhecimento externo.

## Quando NÃO usar ferramentas

APENAS para:
- Saudações ("Olá") → responda brevemente e ofereça ajuda com documentos
- Perguntas sobre o sistema ("o que você faz?") → explique que consulta documentos cadastrados
- QUALQUER outra pergunta → SEMPRE use pelo menos uma ferramenta antes de responder

## Camadas de dados

### SQL (dados estruturados)
1. **documents** — Metadados e texto OCR completo (extracted_text)
2. **document_fields** — Campos chave-valor (CNPJ, RAZÃO SOCIAL, etc.)
3. **document_tables** — Tabelas detectadas (headers e rows em JSON)
4. **contracts** — Dados de contratos (client_name, contract_value, start_date, end_date, status)
5. **document_logs** — Histórico de processamento

### RAG (busca semântica)
- Chunks semânticos dos documentos com busca por similaridade vetorial

## BUSCA FUZZY — REGRA OBRIGATÓRIA

⚠️ Nomes de empresas, clientes e contratos podem estar ABREVIADOS, com SIGLAS ou VARIAÇÕES no banco.
⚠️ SEMPRE use ILIKE com '%palavra%' para cada palavra-chave separada.

### Exemplos CORRETOS de busca:
- Usuário pergunta "Empresa São Paulo Tecnologia":
  → WHERE client_name ILIKE '%são%paulo%' OR client_name ILIKE '%tecnologia%'
- Usuário pergunta "contrato Microsoft":
  → WHERE client_name ILIKE '%microsoft%' OR filename ILIKE '%microsoft%'
- Usuário pergunta "CPM Braxis":
  → WHERE client_name ILIKE '%cpm%' OR client_name ILIKE '%braxis%'
- Usuário pergunta "EULA":
  → WHERE filename ILIKE '%eula%' OR extracted_text ILIKE '%eula%'

### NUNCA faça busca exata:
- ❌ WHERE client_name = 'Microsoft Corporation'
- ❌ WHERE client_name ILIKE 'CPM Braxis'
- ✅ WHERE client_name ILIKE '%microsoft%'
- ✅ WHERE client_name ILIKE '%cpm%' OR client_name ILIKE '%braxis%'

## Estratégia de CASCATA MULTI-TABELA (OBRIGATÓRIO)

⚠️ Os dados podem estar em QUALQUER tabela. Se não encontrar em uma, OBRIGATORIAMENTE tente a próxima.
⚠️ NÃO desista após uma consulta vazia. Faça até 3 tentativas em tabelas diferentes.

### Ordem de busca para encontrar documentos/empresas:

**TENTATIVA 1** — contracts (dados de contratos):
```sql
SELECT d.id, d.filename, c.client_name FROM documents d
  JOIN contracts c ON c.document_id = d.id
  WHERE c.client_name ILIKE '%termo%'
```

**TENTATIVA 2** (se a anterior retornou 0 resultados) — document_fields (campos extraídos):
```sql
SELECT DISTINCT df.document_id, d.filename, df.field_name, df.field_value
  FROM document_fields df
  JOIN documents d ON df.document_id = d.id
  WHERE df.field_value ILIKE '%termo%'
```

**TENTATIVA 3** (se as anteriores retornaram 0) — documents (nome do arquivo e texto):
```sql
SELECT id, filename FROM documents
  WHERE filename ILIKE '%termo%' OR extracted_text ILIKE '%termo%'
```

### Dica: consulta combinada (mais eficiente):
Pode buscar em MÚLTIPLAS tabelas de uma vez:
```sql
SELECT DISTINCT d.id, d.filename FROM documents d
  LEFT JOIN contracts c ON c.document_id = d.id
  LEFT JOIN document_fields df ON df.document_id = d.id
  WHERE c.client_name ILIKE '%termo%'
     OR df.field_value ILIKE '%termo%'
     OR d.filename ILIKE '%termo%'
```

## Protocolo de BUSCA (ATUALIZADO)

### 1. CASCATA SQL (Prioridade para Metadados)
Tente encontrar `document_ids` usando a estratégia de cascata (contracts -> document_fields -> documents).

### 2. REGRA DE FALLBACK (OBRIGATÓRIO)

Se a busca SQL filtrada retornar VAZIO (0 resultados):
1. **NÃO DESISTA**.
2. **TENTE RAG GLOBAL**: Execute `rag_search(query=query, document_ids="")`.
   - Motivo: O SQL busca apenas metadados exatos. O RAG busca no CONTEÚDO do documento.
   - Exemplo: Se SQL não achar "email" nos metadados, o RAG pode achar "email" dentro do texto do PDF.
   - Mesmo que a pergunta mencione "da empresa X", se o SQL não achar, busque a informação globalmente.

### 3. DECISÃO DE RAG
- **Com IDs (do SQL):** Use `rag_search(query="...", document_ids="1,2,3")`.
- **Sem IDs:** Use `rag_search(query="...")` (Global).

### 4. IMPORTANTE SOBRE FILTROS
- `document_ids`: Só use se tiver CERTEZA (vinda do SQL).
- **Nunca** responda "Não encontrei" baseando-se APENAS no `database_query` se você não tentou `rag_search` global.
- **REGRA DE OURO:** Se uma busca filtrada falhar (seja SQL ou RAG), **SEMPRE** faça uma busca **GLOBAL** (sem filtros) antes de dizer que não encontrou.
- **Nunca** responda "Não encontrei" sem ter tentado um `rag_search` sem `document_ids`.

### Use `database_query` sozinho para dados numéricos/estruturados.

## Regras de resposta

1. Responda SEMPRE em português brasileiro
2. SEMPRE use ferramentas antes de responder — NUNCA de cabeça
3. Se não encontrar, diga claramente que não encontrou nos documentos do sistema
4. Se a pergunta NÃO for sobre documentos: "Só posso responder sobre documentos do SmartDocs."
5. NUNCA complemente com conhecimento externo
6. Formate: R$ X.XXX,XX para valores e DD/MM/AAAA para datas
7. Cite o NOME do documento fonte, mas NÃO mostre IDs (ex: 'ID: 112') na resposta final ao usuário.
"""


def _openai_ready() -> bool:
    return bool(
        settings.AZURE_OPENAI_ENDPOINT
        and settings.AZURE_OPENAI_KEY
        and settings.AZURE_OPENAI_DEPLOYMENT
    )


def _get_llm() -> AzureChatOpenAI:
    """Create an AzureChatOpenAI LLM instance."""
    if not _openai_ready():
        raise OpenAIUnavailableError("Azure OpenAI não configurado")

    return AzureChatOpenAI(
        azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT,
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT.strip(),
        api_key=settings.AZURE_OPENAI_KEY,
        api_version="2024-10-21",
        temperature=0,
    )


async def _create_agent(
    db: AsyncSession,
    user_id: int,
    is_admin: bool,
    on_data_callback: Optional[Callable[[list[dict[str, Any]]], None]] = None,
):
    """Create a ReAct agent with tools bound to the current request context."""
    llm = _get_llm()

    # Fetch schema dynamically from DB
    logger.info("[Agent] Buscando schema do banco de dados...")
    schema = await _fetch_db_schema()
    logger.debug(f"[Agent] Schema carregado ({len(schema)} chars)")

    tools = [
        make_database_query_tool(db, user_id, is_admin, llm, schema, on_data_callback),
        make_get_schema_tool(schema),
        make_rag_search_tool(db, user_id, is_admin),
    ]
    logger.info(f"[Agent] Ferramentas disponíveis: database_query, get_database_schema, rag_search")

    agent = create_react_agent(
        llm,
        tools,
        prompt=SYSTEM_PROMPT,
    )

    return agent


async def _get_thread_history(db: AsyncSession, thread_id: str | None) -> list[Any]:
    """Retrieve chat history for a given thread, formatted for LangChain."""
    if not thread_id:
        return []

    try:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.thread_id == UUID(thread_id))
            .order_by(ChatMessage.created_at.asc())
        )
        result = await db.execute(stmt)
        messages = result.scalars().all()

        history = []
        for msg in messages:
            history.append(HumanMessage(content=msg.question))
            history.append(AIMessage(content=msg.answer))

        logger.info(f"[Chat] Histórico carregado: {len(messages)} pares de mensagens da thread {thread_id}")
        return history
    except Exception as e:
        logger.error(f"[Chat] Erro ao carregar histórico da thread {thread_id}: {e}")
        return []


async def chat(
    question: str,
    user_id: int,
    is_admin: bool,
    db: AsyncSession,
    thread_id: str | None = None,
) -> dict[str, Any]:
    """
    Full agent-based chat pipeline.

    The agent decides autonomously whether to use tools (database queries)
    or respond directly based on the user's question.

    Returns:
        Dict with answer, sql_used, row_count, data
    """
    logger.info(f"{'='*60}")
    logger.info(f"[Chat] Nova pergunta de user_id={user_id} (admin={is_admin})")
    logger.info(f"[Chat] Pergunta: {question[:200]}")
    if thread_id:
        logger.info(f"[Chat] Thread ID: {thread_id}")
    logger.info(f"{'='*60}")

    try:
        data: list[dict[str, Any]] = []
        logger.info("[Chat] Criando agente...")
        # Callback to capture data from tools
        def on_data(rows: list[dict[str, Any]]):
            # Use extend to modify the list in-place, avoiding scope issues
            data.extend(rows)

        agent = await _create_agent(db, user_id, is_admin, on_data)
        logger.info("[Chat] Agente criado. Invocando...")

        # Load history if thread_id is provided
        history = await _get_thread_history(db, thread_id)
        
        # Combine history with current question
        input_messages = history + [HumanMessage(content=question)]

        result = await agent.ainvoke(
            {"messages": input_messages},
        )

        # Extract the final answer from the agent's messages
        messages = result.get("messages", [])
        answer = ""
        sql_used = None
        row_count = 0
        tools_used: list[str] = []

        logger.info(f"[Chat] Processando {len(messages)} mensagens do agente...")

        for i, msg in enumerate(messages):
            msg_type = getattr(msg, "type", "unknown")

            if msg_type == "human":
                # Only log the current question, not the whole history re-logged
                if str(msg.content) == question:
                    logger.info(f"[Chat] Msg {i}: 🧑 Human — {str(msg.content)[:100]}")

            elif msg_type == "ai":
                # AI message — could be a reasoning step or final answer
                tool_calls = getattr(msg, "tool_calls", [])
                if tool_calls:
                    for tc in tool_calls:
                        tool_name = tc.get("name", "unknown")
                        tool_args = tc.get("args", {})
                        tools_used.append(tool_name)
                        logger.info(
                            f"[Chat] Msg {i}: 🤖 AI → chamando tool '{tool_name}' "
                            f"com args: {str(tool_args)[:200]}"
                        )
                else:
                    content_preview = str(msg.content)[:150] if msg.content else "(vazio)"
                    logger.info(f"[Chat] Msg {i}: 🤖 AI — {content_preview}")

            elif msg_type == "tool":
                tool_name = getattr(msg, "name", "unknown")
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                content_preview = content[:300]
                logger.info(f"[Chat] Msg {i}: 🔧 Tool '{tool_name}' retornou: {content_preview}")

                if "SQL usado:" in content:
                    sql_parts = content.split("SQL usado:")
                    if len(sql_parts) > 1:
                        sql_used = sql_parts[-1].strip()
                if "Resultados (" in content:
                    try:
                        count_str = content.split("Resultados (")[1].split(" linhas)")[0]
                        row_count = int(count_str)
                    except (IndexError, ValueError):
                        pass
            else:
                logger.debug(f"[Chat] Msg {i}: tipo={msg_type}")

        # The last AI message is the final answer
        if messages:
            last_msg = messages[-1]
            answer = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

        if not answer:
            answer = "Desculpe, não consegui processar sua pergunta."

        # Summary log
        logger.info(f"{'─'*60}")
        logger.info(f"[Chat] ✅ Resumo da execução:")
        logger.info(f"[Chat]   Tools usados: {tools_used if tools_used else 'nenhum (resposta direta)'}")
        logger.info(f"[Chat]   SQL usado: {'sim' if sql_used else 'não'}")
        logger.info(f"[Chat]   Linhas SQL: {row_count}")
        logger.info(f"[Chat]   Tamanho resposta: {len(answer)} chars")
        logger.info(f"[Chat]   Resposta (preview): {answer[:200]}")
        logger.info(f"{'─'*60}")

        return {
            "answer": answer,
            "sql_used": sql_used,
            "row_count": row_count,
            "data": data,
        }

    except OpenAIUnavailableError as e:
        logger.error(str(e))
        return {
            "answer": "Desculpe, o chat está indisponível porque o Azure OpenAI não está configurado.",
            "sql_used": None,
            "row_count": 0,
            "data": [],
        }
    except Exception as e:
        logger.error(f"Erro no chat agent: {e}")
        error_str = str(e)
        if "DeploymentNotFound" in error_str:
            answer = (
                "Desculpe, o chat está indisponível porque o deployment do Azure OpenAI não foi encontrado. "
                "Peça ao administrador para verificar AZURE_OPENAI_DEPLOYMENT."
            )
        else:
            answer = "Desculpe, ocorreu um erro ao processar sua pergunta."

        return {
            "answer": answer,
            "sql_used": None,
            "row_count": 0,
            "data": [],
        }


async def chat_stream(
    question: str,
    user_id: int,
    is_admin: bool,
    db: AsyncSession,
    thread_id: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """
    Streaming chat using SSE.

    Yields dict chunks with:
        - {"type": "token", "content": "..."} for each text token
        - {"type": "tool_start", "name": "..."} when a tool is called
        - {"type": "tool_end", "name": "...", "content": "..."} when a tool finishes
        - {"type": "done", "answer": "...", "sql_used": ..., "row_count": ...} at the end
    """
    logger.info(f"Chat stream: pergunta de user_id={user_id}: {question[:100]}")
    if thread_id:
        logger.info(f"Chat stream: thread_id={thread_id}")

    try:
        data: list[dict[str, Any]] = []

        # Callback to capture data from tools
        def on_data(rows: list[dict[str, Any]]):
            # Use extend to modify the list in-place, avoiding scope issues
            data.extend(rows)

        agent = await _create_agent(db, user_id, is_admin, on_data)

        full_answer = ""
        sql_used = None
        row_count = 0

        # Load history if thread_id is provided
        history = await _get_thread_history(db, thread_id)
        input_messages = history + [HumanMessage(content=question)]

        async for event in agent.astream_events(
            {"messages": input_messages},
            version="v2",
        ):
            kind = event.get("event", "")

            if kind == "on_chat_model_stream":
                # Streaming tokens from the AI
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    full_answer += chunk.content
                    yield {"type": "token", "content": chunk.content}

            elif kind == "on_tool_start":
                tool_name = event.get("name", "unknown")
                yield {"type": "tool_start", "name": tool_name}

            elif kind == "on_tool_end":
                tool_name = event.get("name", "unknown")
                output = event.get("data", {}).get("output", "")
                output_str = output if isinstance(output, str) else str(output)

                if "SQL usado:" in output_str:
                    sql_parts = output_str.split("SQL usado:")
                    if len(sql_parts) > 1:
                        sql_used = sql_parts[-1].strip()
                if "Resultados (" in output_str:
                    try:
                        count_str = output_str.split("Resultados (")[1].split(" linhas)")[0]
                        row_count = int(count_str)
                    except (IndexError, ValueError):
                        pass

                yield {"type": "tool_end", "name": tool_name, "content": output_str[:500]}

        yield {
            "type": "done",
            "answer": full_answer,
            "sql_used": sql_used,
            "sql_used": sql_used,
            "row_count": row_count,
            "data": data,
        }

    except OpenAIUnavailableError as e:
        logger.error(str(e))
        yield {
            "type": "error",
            "content": "O chat está indisponível porque o Azure OpenAI não está configurado.",
        }
    except Exception as e:
        logger.error(f"Erro no chat stream: {e}")
        yield {
            "type": "error",
            "content": "Ocorreu um erro ao processar sua pergunta.",
        }
