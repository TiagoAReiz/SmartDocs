from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import String, Numeric, Date, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_name: Mapped[str | None] = mapped_column(String(512))
    contract_value: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    document = relationship("Document", back_populates="contracts")

    def __repr__(self) -> str:
        return f"<Contract id={self.id} client={self.client_name}>"
