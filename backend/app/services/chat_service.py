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


SYSTEM_PROMPT = """Você é o SmartDocs Assistant, um assistente inteligente de gestão documental.

O SmartDocs processa documentos usando OCR (Azure Document Intelligence) e armazena os dados extraídos em duas camadas complementares:

### Camada ESTRUTURADA (banco de dados SQL)
1. **documents** — Metadados do documento (nome, tipo, status, nº de páginas) e o texto OCR completo (extracted_text)
2. **document_fields** — Campos chave-valor extraídos (ex: "CNPJ" → "12.345.678/0001-00", "RAZÃO SOCIAL" → "Empresa X")
3. **document_tables** — Tabelas detectadas no documento (headers e rows em formato JSON)
4. **contracts** — Dados estruturados de contratos (cliente, valor, datas de início/fim, status)
5. **document_logs** — Histórico de eventos do processamento (upload, extração, erros)

### Camada SEMÂNTICA (RAG com busca vetorial)
- Chunks semânticos dos documentos com embeddings vetoriais
- Permite busca por similaridade de significado, não apenas palavras-chave
- Ideal para encontrar cláusulas, termos, condições e conteúdo descritivo

## Estratégia de ROTEAMENTO (CRÍTICO)

Para CADA pergunta, analise e decida qual(is) ferramenta(s) usar:

### Use `rag_search` quando:
- A pergunta é sobre conteúdo textual, cláusulas, termos, condições
- Busca por informações descritivas ou interpretativas
- Exemplos: "o que diz o contrato sobre...", "quais são as condições de...",
  "qual a cláusula de rescisão", "o que está previsto sobre multa"
- Qualquer busca onde o SIGNIFICADO importa mais que dados exatos

### Use `database_query` quando:
- Precisa de dados estruturados (valores monetários, datas, contagens, status)
- Precisa de campos específicos extraídos (CNPJ, razão social)
- Precisa de agregações ou filtros exatos
- Exemplos: "quantos contratos temos", "qual o valor total",
  "lista de documentos processados", "qual o CNPJ do cliente X"

### Use AMBOS quando:
- A pergunta combina dados estruturados com contexto textual
- Exemplo: "Qual o valor do contrato e o que ele diz sobre multa rescisória?"
- Faça AMBAS as consultas e consolide na resposta final

Você pode ter até 10 chunks do RAG + resultados SQL na mesma análise.
Analise todo o contexto obtido antes de formular a resposta final.

## Estratégia de busca SQL

1. **Primeiro, identifique ONDE o dado pode estar:**
   - Campos específicos (CNPJ, razão social) → `document_fields`
   - Valores, clientes, vigência → `contracts`
   - Conteúdo de texto → `documents.extracted_text` com ILIKE
   - Quantidade, status → `documents`
   - Tabelas numéricas → `document_tables`
   - Processamento, erros → `document_logs`

2. **Se a primeira consulta não retornar resultado, tente outra camada.**

3. **Você pode (e deve) fazer MÚLTIPLAS consultas** para explorar os dados.

## Regras de resposta

1. Responda SEMPRE em português brasileiro
2. Para saudações ou conversa geral, responda diretamente SEM ferramentas
3. Formate valores monetários como R$ X.XXX,XX
4. Formate datas como DD/MM/AAAA
5. Use formatação markdown (negrito, listas, tabelas) para melhor legibilidade
6. Se não encontrar resultados após buscar em todas as camadas, informe educadamente
7. Se houver erro, explique de forma clara e tente reformular
8. Ao apresentar dados de tabelas, formate como tabela markdown
9. Quando tiver muitas linhas, apresente um resumo e pergunte se quer mais detalhes
10. Ao combinar RAG + SQL, apresente uma resposta consolidada e coerente
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
    schema = await _fetch_db_schema()

    tools = [
        make_database_query_tool(db, user_id, is_admin, llm, schema),
        make_get_schema_tool(schema),
        make_rag_search_tool(db, user_id, is_admin),
    ]

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
    logger.info(f"Chat: pergunta recebida de user_id={user_id}: {question[:100]}")

    try:
        agent = await _create_agent(db, user_id, is_admin)

        result = await agent.ainvoke(
            {"messages": [("user", question)]},
        )

        # Extract the final answer from the agent's messages
        messages = result.get("messages", [])
        answer = ""
        sql_used = None
        data: list[dict[str, Any]] = []
        row_count = 0

        for msg in messages:
            # Check for tool messages that contain SQL info
            if hasattr(msg, "type") and msg.type == "tool":
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
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

        # The last AI message is the final answer
        if messages:
            last_msg = messages[-1]
            answer = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

        if not answer:
            answer = "Desculpe, não consegui processar sua pergunta."

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
