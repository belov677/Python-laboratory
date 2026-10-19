"""REST API (дополнительное задание 2): uvicorn src.api.app:app"""
from __future__ import annotations

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.repositories.sqlite_repository import SQLiteInventoryRepository
from src.services.exceptions import (DuplicateError, InsufficientStockError, NotFoundError,
                                     ValidationError, WarehouseError)
from src.services.inventory_service import InventoryService
from src.services.notifier import LogNotifier

app = FastAPI(title="Склад — лабораторная 18")
_service: InventoryService | None = None


def get_service() -> InventoryService:
    """Сервис создаётся при первом запросе (импорт модуля не создаёт файл БД)."""
    global _service
    if _service is None:
        _service = InventoryService(SQLiteInventoryRepository("warehouse.db"), LogNotifier())
    return _service


STATUS = {NotFoundError: 404, ValidationError: 422, DuplicateError: 409, InsufficientStockError: 409}


@app.exception_handler(WarehouseError)
async def domain_error(_request: Request, error: WarehouseError) -> JSONResponse:
    return JSONResponse({"error": type(error).__name__, "detail": str(error)},
                        status_code=STATUS.get(type(error), 400))


class ProductIn(BaseModel):
    sku: str
    name: str
    unit: str = "шт"
    min_stock: int = 0


class WarehouseIn(BaseModel):
    name: str
    city: str


class MoveIn(BaseModel):
    product_id: int
    warehouse_id: int
    quantity: int = Field(description="1…10000")


class TransferIn(BaseModel):
    product_id: int
    source_id: int
    target_id: int
    quantity: int


@app.post("/products", status_code=201)
def create_product(data: ProductIn, service: InventoryService = Depends(get_service)) -> dict:
    return vars(service.create_product(data.sku, data.name, data.unit, data.min_stock))


@app.get("/products")
def search(q: str = "", service: InventoryService = Depends(get_service)) -> list[dict]:
    return [vars(p) for p in service.search(q)]


@app.get("/products/{product_id}/stock")
def stock(product_id: int, service: InventoryService = Depends(get_service)) -> dict:
    product = service.get_product(product_id)
    balances = service.repo.balances(product.id)
    return {"product": vars(product), "balances": balances, "total": sum(balances.values())}


@app.post("/warehouses", status_code=201)
def create_warehouse(data: WarehouseIn, service: InventoryService = Depends(get_service)) -> dict:
    return vars(service.create_warehouse(data.name, data.city))


@app.post("/stock/receive")
def receive(data: MoveIn, service: InventoryService = Depends(get_service)) -> dict:
    return {"balance": service.receive(data.product_id, data.warehouse_id, data.quantity)}


@app.post("/stock/write-off")
def write_off(data: MoveIn, service: InventoryService = Depends(get_service)) -> dict:
    return {"balance": service.write_off(data.product_id, data.warehouse_id, data.quantity)}


@app.post("/stock/transfer")
def transfer(data: TransferIn, service: InventoryService = Depends(get_service)) -> dict:
    source, target = service.transfer(data.product_id, data.source_id, data.target_id, data.quantity)
    return {"source_balance": source, "target_balance": target}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
