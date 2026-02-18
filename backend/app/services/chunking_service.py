"""
Semantic chunking service for document text.

Splits extracted text into semantically meaningful chunks
based on contract/document section patterns, respecting
a maximum token limit per chunk.
"""

import re
from dataclasses import dataclass, field

import tiktoken


# Patterns that indicate section boundaries in contracts/documents
_SECTION_PATTERNS = [
    # CLÁUSULA 1, Cláusula Primeira, CLÁUSULA DÉCIMA
    re.compile(
        r"^(?:CLÁUSULA|Cláusula|CLAUSULA|Clausula)\s+",
        re.MULTILINE,
    ),
    # ARTIGO 1, Art. 1, ARTIGO PRIMEIRO
    re.compile(
        r"^(?:ARTIGO|Artigo|Art\.?)\s+",
        re.MULTILINE,
    ),
    # CAPÍTULO I, Capítulo 1
    re.compile(
        r"^(?:CAPÍTULO|Capítulo|CAPITULO|Capitulo)\s+",
        re.MULTILINE,
    ),
    # SEÇÃO 1, Seção I
    re.compile(
        r"^(?:SEÇÃO|Seção|SECAO|Secao)\s+",
        re.MULTILINE,
    ),
    # PARÁGRAFO, § 1º, Parágrafo Único
    re.compile(
        r"^(?:PARÁGRAFO|Parágrafo|PARAGRAFO|Paragrafo|§\s*\d)",
        re.MULTILINE,
    ),
    # DAS OBRIGAÇÕES, DO OBJETO, DA VIGÊNCIA (uppercase headings)
    re.compile(
        r"^(?:D[OAE]S?\s+[A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][A-ZÀÁÂÃÉÊÍÓÔÕÚÇ\s]{3,})$",
        re.MULTILINE,
    ),
    # Numbered sections: 1., 1.1, 1.1.1
    re.compile(
        r"^\d+(?:\.\d+)*\.\s+[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ]",
        re.MULTILINE,
    ),
]

# Regex for detecting section heading text (for section_type labelling)
_HEADING_CLASSIFIER = {
    "cláusula": re.compile(r"(?:CLÁUSULA|Cláusula|CLAUSULA|Clausula)", re.IGNORECASE),
    "artigo": re.compile(r"(?:ARTIGO|Artigo|Art\.?)\s+\d", re.IGNORECASE),
    "capítulo": re.compile(r"(?:CAPÍTULO|Capítulo|CAPITULO)", re.IGNORECASE),
    "seção": re.compile(r"(?:SEÇÃO|Seção|SECAO)", re.IGNORECASE),
    "parágrafo": re.compile(r"(?:PARÁGRAFO|Parágrafo|§)", re.IGNORECASE),
}

# Tokenizer for counting tokens (same family as GPT-4 / text-embedding-3)
_ENCODING = tiktoken.get_encoding("cl100k_base")


@dataclass
class ChunkData:
    """A single chunk produced by the chunking service."""

    content: str
    section_type: str | None = None
    token_count: int = 0
    chunk_index: int = 0
    metadata: dict = field(default_factory=dict)


def _count_tokens(text: str) -> int:
    """Count tokens using tiktoken cl100k_base encoding."""
    return len(_ENCODING.encode(text))


def _classify_section(text: str) -> str | None:
    """Try to classify the section type from the first line."""
    first_line = text.strip().split("\n")[0] if text.strip() else ""
    for section_type, pattern in _HEADING_CLASSIFIER.items():
        if pattern.search(first_line):
            return section_type
    return "texto_geral"


def _find_section_boundaries(text: str) -> list[int]:
    """Find all positions where a new section starts."""
    boundaries: set[int] = set()
    for pattern in _SECTION_PATTERNS:
        for match in pattern.finditer(text):
            boundaries.add(match.start())
    return sorted(boundaries)


def _split_into_sections(text: str) -> list[str]:
    """Split text into semantic sections based on detected boundaries."""
    boundaries = _find_section_boundaries(text)

    if not boundaries:
        # No sections detected — treat whole text as one block
        return [text] if text.strip() else []

    sections = []

    # Text before the first section boundary
    if boundaries[0] > 0:
        preamble = text[: boundaries[0]].strip()
        if preamble:
            sections.append(preamble)

    # Each section from one boundary to the next
    for i, start in enumerate(boundaries):
        end = boundaries[i + 1] if i + 1 < len(boundaries) else len(text)
        section = text[start:end].strip()
        if section:
            sections.append(section)

    return sections


def _split_long_text(
    text: str,
    max_tokens: int,
    overlap_tokens: int,
) -> list[str]:
    """Split text that exceeds max_tokens into smaller chunks by paragraphs.

    Maintains an overlap of `overlap_tokens` between consecutive chunks
    to preserve context continuity.
    """
    paragraphs = re.split(r"\n\s*\n", text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    if not paragraphs:
        return []

    chunks: list[str] = []
    current_parts: list[str] = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = _count_tokens(para)

        # If a single paragraph exceeds max, split by sentences
        if para_tokens > max_tokens:
            # Flush current buffer first
            if current_parts:
                chunks.append("\n\n".join(current_parts))
                current_parts = []
                current_tokens = 0

            # Split by sentences
            sentences = re.split(r"(?<=[.!?])\s+", para)
            sent_parts: list[str] = []
            sent_tokens = 0
            for sent in sentences:
                st = _count_tokens(sent)
                if sent_tokens + st > max_tokens and sent_parts:
                    chunks.append(" ".join(sent_parts))
                    # Keep last sentence(s) for overlap
                    overlap_parts: list[str] = []
                    overlap_t = 0
                    for s in reversed(sent_parts):
                        overlap_t += _count_tokens(s)
                        if overlap_t > overlap_tokens:
                            break
                        overlap_parts.insert(0, s)
                    sent_parts = overlap_parts
                    sent_tokens = sum(_count_tokens(s) for s in sent_parts)
                sent_parts.append(sent)
                sent_tokens += st
            if sent_parts:
                chunks.append(" ".join(sent_parts))
            continue

        if current_tokens + para_tokens > max_tokens and current_parts:
            chunks.append("\n\n".join(current_parts))

            # Build overlap from the end of current_parts
            overlap_parts: list[str] = []
            overlap_t = 0
            for p in reversed(current_parts):
                pt = _count_tokens(p)
                if overlap_t + pt > overlap_tokens:
                    break
                overlap_parts.insert(0, p)
                overlap_t += pt

            current_parts = overlap_parts
            current_tokens = overlap_t

        current_parts.append(para)
        current_tokens += para_tokens

    if current_parts:
        chunks.append("\n\n".join(current_parts))

    return chunks


def create_chunks(
    extracted_text: str,
    max_tokens: int = 2000,
    overlap_tokens: int = 200,
) -> list[ChunkData]:
    """Create semantic chunks from extracted document text.

    Strategy:
    1. Split text into semantic sections (clauses, articles, chapters, etc.)
    2. If a section fits within max_tokens, keep it as one chunk
    3. If a section exceeds max_tokens, split by paragraphs with overlap
    4. Each chunk gets metadata about its section type

    Args:
        extracted_text: Full OCR-extracted text from the document.
        max_tokens: Maximum tokens per chunk (default 2000).
        overlap_tokens: Token overlap between sub-chunks of a long section.

    Returns:
        List of ChunkData with content, section_type, token_count, etc.
    """
    if not extracted_text or not extracted_text.strip():
        return []

    sections = _split_into_sections(extracted_text)

    chunks: list[ChunkData] = []
    chunk_idx = 0

    for section in sections:
        section_type = _classify_section(section)
        token_count = _count_tokens(section)

        if token_count <= max_tokens:
            # Section fits in one chunk
            chunks.append(
                ChunkData(
                    content=section,
                    section_type=section_type,
                    token_count=token_count,
                    chunk_index=chunk_idx,
                    metadata={"original_section_start": section[:80]},
                )
            )
            chunk_idx += 1
        else:
            # Section too large — split into sub-chunks
            sub_chunks = _split_long_text(section, max_tokens, overlap_tokens)
            # Extract the section heading for context prefix
            first_line = section.strip().split("\n")[0]
            heading_prefix = (
                f"[Continuação de: {first_line[:100]}]\n\n"
                if len(first_line) < 120
                else ""
            )

            for i, sub in enumerate(sub_chunks):
                content = sub if i == 0 else heading_prefix + sub
                tc = _count_tokens(content)
                chunks.append(
                    ChunkData(
                        content=content,
                        section_type=section_type,
                        token_count=tc,
                        chunk_index=chunk_idx,
                        metadata={
                            "original_section_start": first_line[:80],
                            "sub_chunk": i,
                            "total_sub_chunks": len(sub_chunks),
                        },
                    )
                )
                chunk_idx += 1

    return chunks
