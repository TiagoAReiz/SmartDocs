"""
Chat service — LangChain agent with Azure OpenAI.

Uses a ReAct agent that decides autonomously when to query the database
versus responding directly (e.g. greetings, general questions).
"""

import json
from typing import Any, AsyncIterator

from langchain_openai import AzureChatOpenAI
from langgraph.prebuilt import create_react_agent
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.tools import make_database_query_tool, make_get_schema_tool, _fetch_db_schema
from app.services.rag_tool import make_rag_search_tool


class OpenAIUnavailableError(RuntimeError):
    pass


SYSTEM_PROMPT = """Você é o SmartDocs Assistant, um assistente de gestão documental que responde EXCLUSIVAMENTE com base nos documentos armazenados no sistema.

## REGRA ABSOLUTA — FONTE ÚNICA DE VERDADE

⚠️ Você NÃO possui conhecimento próprio. Você NÃO deve usar informações da internet, treinamento, ou conhecimento geral.
⚠️ TODA resposta sobre dados ou conteúdo DEVE vir das ferramentas (database_query ou rag_search).
⚠️ Se as ferramentas não retornarem informação relevante, diga: "Não encontrei essa informação nos documentos cadastrados no sistema."
⚠️ NUNCA invente, suponha, ou complemente com conhecimento externo.

## Quando NÃO usar ferramentas

APENAS para interações básicas do sistema:
- Saudações simples ("Olá", "Bom dia") → responda brevemente e ofereça ajuda com os documentos
- Perguntas sobre o próprio sistema ("o que você faz?") → explique que consulta documentos cadastrados
- Para QUALQUER outra pergunta → SEMPRE use pelo menos uma ferramenta antes de responder

## Camadas de dados disponíveis

### Camada ESTRUTURADA (SQL)
1. **documents** — Metadados e texto OCR completo (extracted_text)
2. **document_fields** — Campos chave-valor (ex: "CNPJ", "RAZÃO SOCIAL")
3. **document_tables** — Tabelas detectadas (headers e rows em JSON)
4. **contracts** — Dados de contratos (cliente, valor, datas, status)
5. **document_logs** — Histórico de processamento

### Camada SEMÂNTICA (RAG)
- Chunks semânticos dos documentos com busca por similaridade
- Ideal para cláusulas, termos, condições, conteúdo descritivo

## Estratégia de busca em 2 ETAPAS (CRÍTICO)

### Quando a pergunta menciona um CLIENTE, EMPRESA, CONTRATO ou DOCUMENTO ESPECÍFICO:

**ETAPA 1** — Use `database_query` para identificar os document_ids relevantes:
- Ex: SELECT d.id, d.filename FROM documents d JOIN contracts c ON c.document_id = d.id WHERE c.client_name ILIKE '%nome%'
- Ou: SELECT id, filename FROM documents WHERE filename ILIKE '%termo%'
- Ou: SELECT DISTINCT document_id FROM document_fields WHERE field_value ILIKE '%empresa%'

**ETAPA 2** — Use `rag_search` passando os document_ids encontrados:
- Ex: rag_search(query="multa rescisória", document_ids="42,87")
- Isso foca a busca APENAS nos documentos corretos

### Quando a pergunta é GENÉRICA (sem mencionar documento/cliente):
- Use `rag_search` sem filtros (busca em todos os documentos)
- Ou use `rag_search` com `document_type` para filtrar por tipo (ex: document_type="contrato")

### Use `database_query` sozinho quando:
- Precisa APENAS de dados estruturados (valores, datas, contagens, status, CNPJ)

### Use AMBOS quando:
- A pergunta combina dados estruturados com contexto textual

## Regras de resposta

1. Responda SEMPRE em português brasileiro
2. SEMPRE use ferramentas antes de responder sobre dados — NUNCA responda de cabeça
3. Se não encontrar dados, diga: "Não encontrei essa informação nos documentos do sistema"
4. Se a pergunta NÃO for sobre documentos, diga: "Só posso responder sobre os documentos cadastrados no SmartDocs."
5. NUNCA complemente com conhecimento externo — use APENAS o que as ferramentas retornaram
6. Formate valores monetários como R$ X.XXX,XX e datas como DD/MM/AAAA
7. Use markdown para legibilidade
8. Cite de qual documento veio a informação (nome do arquivo e ID)
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
):
    """Create a ReAct agent with tools bound to the current request context."""
    llm = _get_llm()

    # Fetch schema dynamically from DB
    logger.info("[Agent] Buscando schema do banco de dados...")
    schema = await _fetch_db_schema()
    logger.debug(f"[Agent] Schema carregado ({len(schema)} chars)")

    tools = [
        make_database_query_tool(db, user_id, is_admin, llm, schema),
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


async def chat(
    question: str,
    user_id: int,
    is_admin: bool,
    db: AsyncSession,
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
    logger.info(f"{'='*60}")

    try:
        logger.info("[Chat] Criando agente...")
        agent = await _create_agent(db, user_id, is_admin)
        logger.info("[Chat] Agente criado. Invocando...")

        result = await agent.ainvoke(
            {"messages": [("user", question)]},
        )

        # Extract the final answer from the agent's messages
        messages = result.get("messages", [])
        answer = ""
        sql_used = None
        data: list[dict[str, Any]] = []
        row_count = 0
        tools_used: list[str] = []

        logger.info(f"[Chat] Processando {len(messages)} mensagens do agente...")

        for i, msg in enumerate(messages):
            msg_type = getattr(msg, "type", "unknown")

            if msg_type == "human":
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

    try:
        agent = await _create_agent(db, user_id, is_admin)

        full_answer = ""
        sql_used = None
        row_count = 0

        async for event in agent.astream_events(
            {"messages": [("user", question)]},
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
            "row_count": row_count,
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
