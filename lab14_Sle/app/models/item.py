from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Item(Base):
    """Товар склада (ORM-модель)."""
    __tablename__ = "items"
    __table_args__ = (CheckConstraint("quantity >= 0", name="ck_items_quantity"),
                      CheckConstraint("price > 0", name="ck_items_price"))

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    category: Mapped[str] = mapped_column(String(100), index=True)
    quantity: Mapped[int]
    min_stock: Mapped[int] = mapped_column(default=0)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    supplier: Mapped[str] = mapped_column(String(150))
    location: Mapped[str] = mapped_column(String(20))
    expiry_date: Mapped[date | None]
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(),
                                                 onupdate=func.now())
