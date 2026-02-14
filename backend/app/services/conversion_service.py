import asyncio
import tempfile
from pathlib import Path

from loguru import logger


async def convert_to_pdf(input_path: str, output_dir: str | None = None) -> str:
    """
    Convert a DOCX, PPTX, or XLSX file to PDF using LibreOffice headless.

    Args:
        input_path: Path to the input file.
        output_dir: Directory for the output PDF. If None, uses a temp directory.

    Returns:
        Path to the generated PDF file.

    Raises:
        RuntimeError: If LibreOffice conversion fails.
    """
    if output_dir is None:
        output_dir = tempfile.mkdtemp()

    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {input_path}")

    logger.info(f"Convertendo {input_file.name} para PDF...")

    process = await asyncio.create_subprocess_exec(
        "libreoffice",
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        output_dir,
        str(input_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        error_msg = stderr.decode() if stderr else "Erro desconhecido"
        logger.error(f"Falha na conversão LibreOffice: {error_msg}")
        raise RuntimeError(f"Falha na conversão para PDF: {error_msg}")

    # The output file has the same name but with .pdf extension
    output_path = Path(output_dir) / f"{input_file.stem}.pdf"

    if not output_path.exists():
        raise RuntimeError(f"Arquivo PDF não gerado: {output_path}")

    logger.info(f"Conversão concluída: {output_path}")
    return str(output_path)
