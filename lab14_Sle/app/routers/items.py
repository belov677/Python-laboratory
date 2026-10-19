"""HTTP-слой ресурса /items: только разбор запроса и вызов сервиса."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response, status

from config import settings
from dependencies import get_current_user, get_item_service, require_admin
from schemas.item import (ItemCreate, ItemListResponse, ItemReplace, ItemResponse,
                          ItemStatistics, ItemUpdate, SortField, SortOrder)
from services.item import ItemService

router = APIRouter(prefix="/items", tags=["Товары склада"])
log = logging.getLogger("items")
ERRORS = {401: {"description": "Нет или неверный токен"},
          404: {"description": "Товар не найден"}}


def write_audit(action: str, item_id: int, username: str) -> None:
    """Фоновая задача: запись в журнал аудита после отправки ответа клиенту."""
    with open(settings.audit_log, "a", encoding="utf-8") as file:
        file.write(json.dumps({"time": datetime.now().isoformat(timespec="seconds"),
                               "action": action, "item_id": item_id, "user": username},
                              ensure_ascii=False) + "\n")


@router.get("", response_model=ItemListResponse, summary="Список товаров",
            description="Фильтрация, сортировка и пагинация (skip/limit).")
def list_items(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100),
               sort: SortField = "id", order: SortOrder = "asc",
               category: str | None = Query(None, examples=["электроника"]),
               supplier: str | None = None, min_quantity: int | None = Query(None, ge=0),
               below_min: bool | None = None,
               service: ItemService = Depends(get_item_service), _=Depends(get_current_user)):
    items, total = service.list(skip=skip, limit=limit, sort=sort, order=order,
                                category=category, supplier=supplier,
                                min_quantity=min_quantity, below_min=below_min)
    return ItemListResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/search", response_model=list[ItemResponse], summary="Поиск товаров",
            description="Поиск по названию, артикулу и поставщику (без учёта регистра).")
def search_items(q: str = Query(min_length=2, examples=["lenovo"]),
                 service: ItemService = Depends(get_item_service), _=Depends(get_current_user)):
    return service.search(q)


@router.get("/statistics", response_model=ItemStatistics, summary="Статистика склада")
async def statistics(service: ItemService = Depends(get_item_service),
                     _=Depends(get_current_user)):
    """Асинхронный endpoint: запрос к БД выполняется в пуле потоков, event loop свободен."""
    return await asyncio.to_thread(service.statistics)


@router.get("/{item_id}", response_model=ItemResponse, summary="Товар по id",
            responses=ERRORS, description="Кэшируется в Redis (заголовок X-Cache: HIT/MISS).")
def get_item(item_id: int, response: Response, service: ItemService = Depends(get_item_service),
             _=Depends(get_current_user)):
    data, source = service.get(item_id)
    response.headers["X-Cache"] = source
    return data


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED,
             summary="Создать товар", responses={409: {"description": "Артикул уже существует"},
                                                 403: {"description": "Нужна роль ADMIN"}})
def create_item(data: ItemCreate, background: BackgroundTasks,
                service: ItemService = Depends(get_item_service), user=Depends(require_admin)):
    item = service.create(data)
    background.add_task(write_audit, "create", item.id, user.username)
    background.add_task(service.cache.publish, "item.created", item.id)
    return item


@router.put("/{item_id}", response_model=ItemResponse, summary="Полностью изменить товар",
            responses=ERRORS)
def replace_item(item_id: int, data: ItemReplace, background: BackgroundTasks,
                 service: ItemService = Depends(get_item_service), user=Depends(require_admin)):
    item = service.replace(item_id, data)
    background.add_task(write_audit, "replace", item_id, user.username)
    return item


@router.patch("/{item_id}", response_model=ItemResponse, summary="Частично изменить товар",
              responses=ERRORS)
def update_item(item_id: int, data: ItemUpdate, background: BackgroundTasks,
                service: ItemService = Depends(get_item_service), user=Depends(require_admin)):
    item = service.update(item_id, data)
    background.add_task(write_audit, "update", item_id, user.username)
    background.add_task(service.cache.publish, "item.updated", item_id)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить товар",
               responses=ERRORS)
def delete_item(item_id: int, background: BackgroundTasks,
                service: ItemService = Depends(get_item_service), user=Depends(require_admin)):
    service.delete(item_id)
    background.add_task(write_audit, "delete", item_id, user.username)
    background.add_task(service.cache.publish, "item.deleted", item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
