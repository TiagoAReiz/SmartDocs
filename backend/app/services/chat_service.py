from typing import Any

from loguru import logger
from openai import AzureOpenAI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.sql_guard import validate_sql, SQLGuardError


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

Regras:
1. Gere APENAS SELECT queries válidas para PostgreSQL
2. NUNCA use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE
3. Use JOINs quando necessário para relacionar tabelas
4. Sempre inclua aliases descritivos para as colunas
5. Para datas, use funções PostgreSQL (NOW(), INTERVAL, etc.)
6. Retorne APENAS o SQL, sem explicações, sem markdown, sem blocos de código
7. Use aspas duplas para nomes de colunas com espaços ou caracteres especiais
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
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        api_key=settings.AZURE_OPENAI_KEY,
        api_version="2024-10-21",
    )


async def generate_sql(question: str) -> str:
    """Generate SQL from a natural language question using Azure OpenAI."""
    client = _get_openai_client()

    response = client.chat.completions.create(
        model=settings.AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        temperature=0.0,
        max_tokens=500,
    )

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

    response = client.chat.completions.create(
        model=settings.AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=1000,
    )

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
    sql = await generate_sql(question)

    # Step 2: Validate SQL with guardrails
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            validated_sql = validate_sql(sql, user_id=user_id, is_admin=is_admin)
            break
        except SQLGuardError as e:
            if attempt < max_retries:
                logger.warning(f"SQL inválido (tentativa {attempt + 1}): {e}")
                # Ask the LLM to fix the SQL
                client = _get_openai_client()
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
                sql = fix_response.choices[0].message.content.strip()
                if sql.startswith("```"):
                    lines = sql.split("\n")
                    sql = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
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
        logger.error(f"Erro ao executar SQL: {e}")
        return {
            "answer": f"Desculpe, ocorreu um erro ao consultar o banco de dados: {e}",
            "sql_used": validated_sql,
            "row_count": 0,
            "data": [],
        }

    # Step 4: Generate answer
    answer = await generate_answer(question, validated_sql, results, row_count)

    return {
        "answer": answer,
        "sql_used": validated_sql,
        "row_count": row_count,
        "data": results,
    }
