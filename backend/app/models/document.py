import enum
from datetime import datetime

from sqlalchemy import (
    String,
    Text,
    Integer,
    Float,
    ForeignKey,
    DateTime,
    JSON,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    original_extension: Mapped[str] = mapped_column(String(20), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    type: Mapped[str | None] = mapped_column(String(50))  # contrato, relatorio, etc.
    page_count: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[DocumentStatus] = mapped_column(
        String(20), nullable=False, default=DocumentStatus.UPLOADED, index=True
    )
    blob_url: Mapped[str | None] = mapped_column(String(1024))
    extracted_text: Mapped[str | None] = mapped_column(Text)
    raw_json: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user = relationship("User", back_populates="documents")
    fields = relationship(
        "DocumentField", back_populates="document", cascade="all, delete-orphan", lazy="selectin"
    )
    tables = relationship(
        "DocumentTable", back_populates="document", cascade="all, delete-orphan", lazy="selectin"
    )
    contracts = relationship(
        "Contract", back_populates="document", cascade="all, delete-orphan", lazy="selectin"
    )
    logs = relationship(
        "DocumentLog", back_populates="document", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} filename={self.filename} status={self.status}>"


class DocumentField(Base):
    __tablename__ = "document_fields"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field_key: Mapped[str] = mapped_column(String(255), nullable=False)
    field_value: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    bounding_box: Mapped[dict | None] = mapped_column(JSON)
    page_number: Mapped[int | None] = mapped_column(Integer)

    # Relationships
    document = relationship("Document", back_populates="fields")

    def __repr__(self) -> str:
        return f"<DocumentField id={self.id} key={self.field_key}>"


class DocumentTable(Base):
    __tablename__ = "document_tables"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    table_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer)
    headers: Mapped[list | None] = mapped_column(JSON)
    rows: Mapped[list | None] = mapped_column(JSON)

    # Relationships
    document = relationship("Document", back_populates="tables")

    def __repr__(self) -> str:
        return f"<DocumentTable id={self.id} index={self.table_index}>"
