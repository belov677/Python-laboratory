"""ORM-модели: пользователь, склад, поставщик, товар, остаток, операция."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    full_name: Mapped[str] = mapped_column(String(150))
    username: Mapped[str | None] = mapped_column(String(64))
    messages: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Warehouse(Base):
    __tablename__ = "warehouses"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    city: Mapped[str] = mapped_column(String(100))


class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    phone: Mapped[str] = mapped_column(String(30))
    products: Mapped[list["Product"]] = relationship(back_populates="supplier")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (CheckConstraint("price > 0"), CheckConstraint("min_stock >= 0"))
    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    price: Mapped[float]
    min_stock: Mapped[int]
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id", ondelete="RESTRICT"))
    supplier: Mapped[Supplier] = relationship(back_populates="products", lazy="joined")
    stocks: Mapped[list["Stock"]] = relationship(back_populates="product",
                                                 cascade="all, delete-orphan", lazy="selectin")

    @property
    def total(self) -> int:
        return sum(s.quantity for s in self.stocks)

    @property
    def is_critical(self) -> bool:
        return self.total < self.min_stock


class Stock(Base):
    """Остаток товара на складе."""
    __tablename__ = "stocks"
    __table_args__ = (UniqueConstraint("product_id", "warehouse_id"),
                      CheckConstraint("quantity >= 0", name="ck_quantity_non_negative"))
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id", ondelete="RESTRICT"))
    quantity: Mapped[int] = mapped_column(default=0)
    product: Mapped[Product] = relationship(back_populates="stocks")
    warehouse: Mapped[Warehouse] = relationship(lazy="joined")


class Operation(Base):
    """Журнал движения товара: поступление (+) и списание (−)."""
    __tablename__ = "operations"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(10))  # receipt / writeoff
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    quantity: Mapped[int]
    user_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    product: Mapped[Product] = relationship(lazy="joined")
    warehouse: Mapped[Warehouse] = relationship(lazy="joined")
