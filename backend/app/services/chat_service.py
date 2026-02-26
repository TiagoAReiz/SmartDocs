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
⚠️ Você NÃO possui conhecimento próprio. Toda resposta DEVE vir das ferramentas.
⚠️ NUNCA invente, suponha ou complemente com conhecimento externo. Se não encontrar, diga que não encontrou nos documentos.
⚠️ IMPORTANTE SOBRE NOMENCLATURA: Os usuários frequentemente se referem a qualquer documento do sistema simplesmente como "contrato" (mesmo que seja uma NF, recibo, etc). Quando o usuário disser "contrato", assuma que ele pode estar falando de qualquer registro na tabela `documents` (ou consulte os metadados/arquivos associados), a menos que o contexto exija estritamente um tipo específico de documento.

## QUANDO NÃO USAR FERRAMENTAS
APENAS para: Saudações ("Olá") ou perguntas sobre você ("o que você faz?"). Qualquer outra coisa, USE UMA FERRAMENTA.

## ESCOLHENDO A FERRAMENTA CERTA (RAG vs SQL)
Você tem duas ferramentas principais para buscar dados: `rag_search` e `database_query`. Avalie a pergunta para escolher a melhor abordagem:

### USE `database_query` (SQL) DIRETAMENTE QUANDO:
- A pergunta envolver **Datas** (ex: "documentos de hoje", "contratos do mês passado").
- A pergunta envolver **Contagens ou Agregações** (ex: "Quantos documentos existem?", "Qual o valor total?").
- A pergunta for um **Relatório ou Listagem Geral** (ex: "Quais os últimos 15 documentos?", "Liste os contratos ativos").
- A pergunta filtrar por **Status** ou metadados básicos (ex: "Quantos falharam?").

### USE `rag_search` (Busca Híbrida) QUANDO:
- A pergunta buscar **Conteúdo Específico ou Nomes Próprios** escondidos no texto (ex: "Qual o email da Marina?", "Quem é o responsável financeiro do contrato X?").
- A pergunta envolver **Cláusulas ou Regras de Negócio** texto-pesadas (ex: "Quais são as regras de rescisão?", "O que diz a cláusula 5?").
- **FALLBACK OBRIGATÓRIO**: Se você usou o SQL e encontrou o documento, mas o dado procurado (ex: nome, CNPJ, email) retornou vazio/`None` ou não estava em `document_fields`, VOCÊ DEVE imediatamente usar o `rag_search` para buscar dentro do `extracted_text` desse documento antes de responder ao usuário. NUNCA desista após um SQL vazio se o RAG ainda não foi tentado.

## PROTOCOLO DE EXTRAÇÃO DE DADOS (PÓS-BUSCA)
Quando você encontrar os arquivos relevantes (seja via RAG ou SQL inicial), você frequentemente precisará buscar os dados exatos extraídos para montar sua resposta final.
Se a resposta depender de campos específicos (CNPJ, Valor, Nome) ou de tabelas (Itens de NF, Produtos), use `database_query` com os IDs dos documentos encontrados:

**PASSO 1: document_fields (Busca nas extrações dinâmicas)**
Se você precisar da Razão Social, CNPJ ou Nome associado a um documento:
```sql
SELECT document_id, field_key, field_value FROM document_fields WHERE document_id = X
```

⚠️ REGRA CRÍTICA DE SQL: SEMPRE, sem exceções, inclua a coluna `id` (ou `document_id`) nas suas queries SQL (ex: `SELECT d.id as document_id, d.filename...`). Se você não retornar o ID verdadeiro do banco, você não saberá qual ID passar para o `rag_search` no fallback e acabará inventando IDs falsos (como '1' ou '2').

**PASSO 2: document_tables (Busca nas tabelas extraídas)**
Se for uma informação tabelada (ex: lista de produtos, itens de nota fiscal):
```sql
SELECT dt.document_id, d.filename, dt.headers, dt.rows FROM document_tables dt
JOIN documents d ON dt.document_id = d.id WHERE d.id = X
```

⚠️ Limite suas pesquisas geradas a `LIMIT 10` ou `LIMIT 5`. 

## REGRAS FINAIS DE RESPOSTA
1. Responda em português brasileiro.
2. Sempre cite o NOME do documento em que você se baseou.
3. Formate valores financeiros para R$ X.XXX,XX quando aplicável.
4. Prepare-se para compilar sua resposta final em um formato estruturado que incluirá a query principal e as referências rastreáveis.
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
        total_messages = len(messages)
        for i, msg in enumerate(messages):
            history.append(HumanMessage(content=msg.question))

            # Resumo automático do AI para economizar tokens na memória do chat
            is_last_message = (i == total_messages - 1)
            
            # Se não é a última mensagem, e ela gerou dezenas de linhas no SQL ou tem mais de 500 chars (muitas vezes tabelas renderizadas), nós a encurtamos
            if not is_last_message and (msg.row_count > 0 or len(msg.answer) > 500):
                if msg.row_count > 0:
                    summary = f"[Resumo de contexto AI: O sistema retornou uma tabela com {msg.row_count} linhas nesta iteração. Resposta truncada para economizar tokens.]"
                else:
                    summary = f"[Resumo de contexto AI: Resposta textual muito longa do assistente omitida nesta iteração para economizar tokens.]"
                history.append(AIMessage(content=summary))
            else:
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
        Dict with answer, sql_used, row_count, data, structured_data
    """
    logger.info(f"{'='*60}")
    logger.info(f"[Chat] Nova pergunta de user_id={user_id} (admin={is_admin})")
    logger.info(f"[Chat] Pergunta: {question[:200]}")
    if thread_id:
        logger.info(f"[Chat] Thread ID: {thread_id}")
    logger.info(f"{'='*60}")

    try:
        data: list[dict[str, Any]] = []
        documents_map: dict[str, dict[str, Any]] = {}

        logger.info("[Chat] Criando agente principal (Fase 1)...")
        # Callback to capture data from tools
        def on_data(rows: list[dict[str, Any]]):
            # Use extend to modify the list in-place, avoiding scope issues
            data.extend(rows)
            # Build document map for Phase 2
            for row in rows:
                doc_id = str(row.get("document_id") or row.get("id"))
                if doc_id and doc_id != "None":
                    if doc_id not in documents_map:
                        documents_map[doc_id] = {
                            "id": doc_id,
                            "filename": row.get("filename"),
                            "sql_fields": [],
                            "sql_tables": []
                        }
                    # We could try to infer if it's a field or table here or simply pass everything we found
                    documents_map[doc_id]["sql_fields"].append(row)

        agent = await _create_agent(db, user_id, is_admin, on_data)
        logger.info("[Chat] Agente Fase 1 criado. Invocando...")

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

        # Summary log Fase 1
        logger.info(f"{'─'*60}")
        logger.info(f"[Chat] ✅ Resumo da execução (Fase 1):")
        logger.info(f"[Chat]   Tools usados: {tools_used if tools_used else 'nenhum (resposta direta)'}")
        logger.info(f"[Chat]   SQL usado: {'sim' if sql_used else 'não'}")
        logger.info(f"[Chat]   Linhas SQL: {row_count}")
        logger.info(f"[Chat]   Tamanho resposta: {len(answer)} chars")
        logger.info(f"[Chat]   Resposta raw: {answer[:200]}")
        logger.info(f"{'─'*60}")

        # ==== PHASE 2: STRUCTURED OUTPUT ====
        logger.info("[Chat] Iniciando Fase 2 (Processamento Estruturado)...")
        structured_data = None
        try:
            from app.schemas.chat import StructuredChatResponse
            from langchain_core.prompts import ChatPromptTemplate
            
            structured_llm = _get_llm().with_structured_output(StructuredChatResponse)
            
            phase2_prompt = ChatPromptTemplate.from_messages([
                ("system", 
                 "Você é um analisador de dados estrito. Sua ÚNICA tarefa é converter a "
                 "resposta final e os dados encontrados na Fase 1 em um objeto JSON exato.\n\n"
                 "Mapeie os documentos referenciados, os campos relevantes e as tabelas "
                 "apenas formatando o que foi extraído pelas ferramentas.\n"
                 "🚨 REGRA CRÍTICA PARA 'message': Você DEVE copiar a 'raw_answer' EXATAMENTE como ela é. "
                 "NUNCA resuma, nunca corte, nunca remova detalhes. A chave `message` deve ser uma cópia integral do texto passado.\n\n"
                 "Aqui estão os documentos extraídos do banco de dados na Fase 1:\n{documents_meta}"),
                ("human", "Pergunta original do usuário: {question}\n\nResposta RAW da Fase 1:\n{raw_answer}")
            ])
            
            chain = phase2_prompt | structured_llm
            structured_data = await chain.ainvoke({
                "question": question,
                "raw_answer": answer,
                "documents_meta": str(documents_map) if documents_map else "Nenhum documento retornado diretamente via ferramenta SQL."
            })
            
            if structured_data:
                # Force fallback override to guarantee phase 1 length representation bypassing strict JSON token culling
                structured_data.message = answer
                logger.info(f"[Chat] Fase 2 concluída com sucesso. Message mapeada.")
                # We overwrite the raw answer with the structured message for cleaner frontend display
                answer = structured_data.message
            else:
                logger.warning("[Chat] Fase 2 retornou nulo. Usando fallback.")

        except Exception as e:
            logger.error(f"[Chat] Falha na Fase 2 (Structured Output): {e}")
            from app.schemas.chat import StructuredChatResponse
            # Fallback
            structured_data = StructuredChatResponse(
                message=answer,
                final_query=sql_used,
                documents=[]
            )

        logger.info(f"{'='*60}")
        return {
            "answer": answer,
            "sql_used": sql_used,
            "row_count": row_count,
            "data": data,
            "structured_data": structured_data.model_dump() if structured_data else None
        }

    except OpenAIUnavailableError as e:
        logger.error(str(e))
        return {
            "answer": "Desculpe, o chat está indisponível porque o Azure OpenAI não está configurado.",
            "sql_used": None,
            "row_count": 0,
            "data": [],
            "structured_data": None
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
            "structured_data": None
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
        documents_map: dict[str, dict[str, Any]] = {}

        # Callback to capture data from tools
        def on_data(rows: list[dict[str, Any]]):
            # Use extend to modify the list in-place, avoiding scope issues
            data.extend(rows)
            # Build document map for Phase 2
            for row in rows:
                doc_id = str(row.get("document_id") or row.get("id"))
                if doc_id and doc_id != "None":
                    if doc_id not in documents_map:
                        documents_map[doc_id] = {
                            "id": doc_id,
                            "filename": row.get("filename"),
                            "sql_fields": [],
                            "sql_tables": []
                        }
                    documents_map[doc_id]["sql_fields"].append(row)

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

        # ==== PHASE 2: STRUCTURED OUTPUT ====
        logger.info("[Chat Stream] Iniciando Fase 2 (Processamento Estruturado)...")
        structured_data = None
        try:
            from app.schemas.chat import StructuredChatResponse
            from langchain_core.prompts import ChatPromptTemplate
            
            structured_llm = _get_llm().with_structured_output(StructuredChatResponse)
            
            phase2_prompt = ChatPromptTemplate.from_messages([
                ("system", 
                 "Você é um analisador de dados estrito. Sua ÚNICA tarefa é converter a "
                 "resposta final e os dados encontrados na Fase 1 em um objeto JSON exato.\n\n"
                 "Mapeie os documentos referenciados, os campos relevantes e as tabelas "
                 "apenas formatando o que foi extraído pelas ferramentas.\n"
                 "🚨 REGRA CRÍTICA PARA 'message': Você DEVE copiar a 'raw_answer' EXATAMENTE como ela é. "
                 "NUNCA resuma, nunca corte, nunca remova detalhes. A chave `message` deve ser uma cópia integral do texto passado.\n\n"
                 "Aqui estão os documentos extraídos do banco de dados na Fase 1:\n{documents_meta}"),
                ("human", "Pergunta original do usuário: {question}\n\nResposta RAW da Fase 1:\n{raw_answer}")
            ])
            
            chain = phase2_prompt | structured_llm
            structured_data = await chain.ainvoke({
                "question": question,
                "raw_answer": full_answer,
                "documents_meta": str(documents_map) if documents_map else "Nenhum documento retornado diretamente via ferramenta SQL."
            })
            
            if structured_data:
                # Force fallback override to guarantee phase 1 length representation bypassing strict JSON token culling
                structured_data.message = full_answer
                if structured_data.message:
                    full_answer = structured_data.message
        except Exception as e:
            logger.error(f"[Chat Stream] Falha na Fase 2: {e}")
            from app.schemas.chat import StructuredChatResponse
            structured_data = StructuredChatResponse(message=full_answer, final_query=sql_used, documents=[])

        yield {
            "type": "done",
            "answer": full_answer,
            "sql_used": sql_used,
            "row_count": row_count,
            "data": data,
            "structured_data": structured_data.model_dump() if structured_data else None
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
