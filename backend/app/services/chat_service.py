from typing import Any

from loguru import logger
from openai import AzureOpenAI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.sql_guard import validate_sql, SQLGuardError


class OpenAIUnavailableError(RuntimeError):
    pass


# Database schema description for the LLM prompt
DB_SCHEMA = """
Tabelas disponíveis:

1. documents (id, user_id, filename, original_extension, mime_type, type, page_count, status, extracted_text, created_at)
2. document_fields (id, document_id, field_key, field_value, confidence, page_number)
3. document_tables (id, document_id, table_index, page_number, headers, rows)
4. contracts (id, document_id, client_name, contract_value, start_date, end_date, status)
5. users (id, name, email, role, created_at)

Relacionamentos:
- documents.user_id → users.id
- document_fields.document_id → documents.id
- document_tables.document_id → documents.id
- contracts.document_id → documents.id
"""

SYSTEM_PROMPT = f"""Você é um assistente de SQL que gera queries PostgreSQL baseadas em perguntas em linguagem natural.
{DB_SCHEMA}

Regras gerais:
1. Gere APENAS SELECT queries válidas para PostgreSQL
2. NUNCA use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE
3. Use JOINs quando necessário para relacionar tabelas
4. Sempre inclua aliases descritivos para as colunas
5. Para datas, use funções PostgreSQL (NOW(), INTERVAL, etc.)
6. Retorne APENAS o SQL, sem explicações, sem markdown, sem blocos de código
7. Use aspas duplas para nomes de colunas com espaços ou caracteres especiais

Regras obrigatórias do projeto:
8. Sempre inclua a tabela documents no FROM sem alias (use exatamente "documents")
9. Quando consultar outras tabelas, sempre relacione com documents (ex.: JOIN document_fields df ON df.document_id = documents.id)
10. Para perguntas sobre contratos assinados, prefira buscar em document_fields usando chaves como "DATA DE ASSINATURA", "CONTRATO Nº", "RAZÃO SOCIAL", "CNPJ"
11. Quando a data estiver em texto DD/MM/AAAA, filtre usando to_date(valor, 'DD/MM/YYYY') = DATE 'YYYY-MM-DD'
12. Para consolidar dados de várias chaves do mesmo documento, use agregação com MAX(CASE WHEN ... THEN ... END) e GROUP BY documents.id
13. Nunca use SELECT *; selecione apenas colunas necessárias e use aliases amigáveis
14. Nunca aplique to_date em document_fields.field_value sem antes filtrar a chave do campo (ex.: df.field_key ILIKE 'DATA DE ASSINATURA:%')
"""

ANSWER_PROMPT = """Dado os resultados da query SQL abaixo, responda a pergunta do usuário em português brasileiro de forma clara e amigável.

Pergunta: {question}
SQL executado: {sql}
Resultados ({row_count} linhas):
{results}

Regras:
1. Responda em PT-BR
2. Formate valores monetários como R$ X.XXX,XX
3. Formate datas como DD/MM/AAAA
4. Se houver muitos resultados, destaque os mais importantes
5. Use formatação markdown (negrito, listas) para melhor legibilidade
6. Se não houver resultados, informe educadamente
"""


def _get_openai_client() -> AzureOpenAI:
    """Create an Azure OpenAI client."""
    return AzureOpenAI(
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT.strip(),
        api_key=settings.AZURE_OPENAI_KEY,
        api_version="2024-10-21",
    )


def _openai_ready() -> bool:
    return bool(
        settings.AZURE_OPENAI_ENDPOINT
        and settings.AZURE_OPENAI_KEY
        and settings.AZURE_OPENAI_DEPLOYMENT
    )


def _openai_error_message(error: Exception | str) -> str:
    base = (
        "Falha ao acessar Azure OpenAI. "
        f"Deployment: {settings.AZURE_OPENAI_DEPLOYMENT}. "
        f"Erro: {error}"
    )
    if "DeploymentNotFound" in str(error):
        return (
            f"{base} "
            "Dica: verifique no Azure OpenAI Studio se o deployment existe e se "
            "AZURE_OPENAI_DEPLOYMENT está com o nome exato do deployment (não o nome do modelo)."
        )
    return base


async def generate_sql(question: str) -> str:
    """Generate SQL from a natural language question using Azure OpenAI."""
    if not _openai_ready():
        raise OpenAIUnavailableError("Azure OpenAI não configurado")
    client = _get_openai_client()

    try:
        response = client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
            temperature=0.0,
            max_tokens=500,
        )
    except Exception as e:
        raise OpenAIUnavailableError(_openai_error_message(e)) from e

    sql = response.choices[0].message.content.strip()

    # Clean up markdown code blocks if the model wraps the SQL
    if sql.startswith("```"):
        lines = sql.split("\n")
        sql = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        sql = sql.strip()

    logger.info(f"SQL gerado: {sql[:200]}")
    return sql


async def execute_query(sql: str, db: AsyncSession) -> list[dict[str, Any]]:
    """Execute a validated SQL query and return results as list of dicts."""
    result = await db.execute(text(sql))
    columns = list(result.keys())
    rows = result.fetchall()

    return [dict(zip(columns, row)) for row in rows]


async def generate_answer(
    question: str,
    sql: str,
    results: list[dict[str, Any]],
    row_count: int,
) -> str:
    """Generate a natural language answer from query results using Azure OpenAI."""
    if not _openai_ready():
        raise OpenAIUnavailableError("Azure OpenAI não configurado")
    client = _get_openai_client()

    # Format results for the prompt
    results_text = str(results[:20])  # Limit to 20 rows for the prompt
    if row_count > 20:
        results_text += f"\n... e mais {row_count - 20} linhas"

    prompt = ANSWER_PROMPT.format(
        question=question,
        sql=sql,
        row_count=row_count,
        results=results_text,
    )

    try:
        response = client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1000,
        )
    except Exception as e:
        raise OpenAIUnavailableError(_openai_error_message(e)) from e

    answer = response.choices[0].message.content.strip()
    return answer


async def chat(
    question: str,
    user_id: int,
    is_admin: bool,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Full NL → SQL → Response pipeline.

    1. Generate SQL from question
    2. Validate with SQL guard
    3. Execute query
    4. Generate natural language response

    Returns:
        Dict with answer, sql_used, row_count, data
    """
    logger.info(f"Chat: pergunta recebida de user_id={user_id}: {question[:100]}")

    # Step 1: Generate SQL
    try:
        sql = await generate_sql(question)
    except OpenAIUnavailableError as e:
        logger.error(str(e))
        if "DeploymentNotFound" in str(e):
            answer = (
                "Desculpe, o chat está indisponível porque o deployment do Azure OpenAI não foi encontrado. "
                "Peça ao administrador para verificar AZURE_OPENAI_DEPLOYMENT."
            )
        else:
            answer = "Desculpe, o chat está indisponível porque o Azure OpenAI não respondeu."
        return {
            "answer": answer,
            "sql_used": None,
            "row_count": 0,
            "data": [],
        }

    # Step 2: Validate SQL with guardrails
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            validated_sql = validate_sql(sql, user_id=user_id, is_admin=is_admin)
            break
        except SQLGuardError as e:
            if attempt < max_retries:
                logger.warning(f"SQL inválido (tentativa {attempt + 1}): {e}")
                if not _openai_ready():
                    return {
                        "answer": "Desculpe, não consegui corrigir o SQL porque o Azure OpenAI não está configurado.",
                        "sql_used": sql,
                        "row_count": 0,
                        "data": [],
                    }
                client = _get_openai_client()
                try:
                    fix_response = client.chat.completions.create(
                        model=settings.AZURE_OPENAI_DEPLOYMENT,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": question},
                            {"role": "assistant", "content": sql},
                            {
                                "role": "user",
                                "content": f"O SQL gerado é inválido: {e}. Corrija gerando apenas SELECT válido.",
                            },
                        ],
                        temperature=0.0,
                        max_tokens=500,
                    )
                except Exception as openai_error:
                    logger.error(_openai_error_message(openai_error))
                    return {
                        "answer": "Desculpe, o chat está indisponível porque o Azure OpenAI não respondeu.",
                        "sql_used": None,
                        "row_count": 0,
                        "data": [],
                    }
                sql = fix_response.choices[0].message.content.strip()
                if sql.startswith("```"):
                    lines = sql.split("\n")
                    sql = "\n".join(
                        lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
                    )
                    sql = sql.strip()
            else:
                logger.error(f"SQL inválido após {max_retries} tentativas: {e}")
                return {
                    "answer": f"Desculpe, não consegui gerar uma consulta válida para sua pergunta. Erro: {e}",
                    "sql_used": sql,
                    "row_count": 0,
                    "data": [],
                }

    # Step 3: Execute query
    try:
        results = await execute_query(validated_sql, db)
        row_count = len(results)
    except Exception as e:
        await db.rollback()
        logger.error(f"Erro ao executar SQL: {e}")
        return {
            "answer": f"Desculpe, ocorreu um erro ao consultar o banco de dados: {e}",
            "sql_used": validated_sql,
            "row_count": 0,
            "data": [],
        }

    # Step 4: Generate answer
    try:
        answer = await generate_answer(question, validated_sql, results, row_count)
    except OpenAIUnavailableError as e:
        logger.error(str(e))
        if "DeploymentNotFound" in str(e):
            answer = (
                "Desculpe, não foi possível gerar a resposta porque o deployment do Azure OpenAI não foi encontrado. "
                "Peça ao administrador para verificar AZURE_OPENAI_DEPLOYMENT."
            )
        else:
            answer = "Desculpe, não foi possível gerar a resposta com o Azure OpenAI."
        return {
            "answer": answer,
            "sql_used": validated_sql,
            "row_count": row_count,
            "data": results,
        }

    return {
        "answer": answer,
        "sql_used": validated_sql,
        "row_count": row_count,
        "data": results,
    }
