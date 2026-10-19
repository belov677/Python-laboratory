-- Индекс для фильтрации товаров по категории (GET /items?category=...) и JOIN с categories
CREATE INDEX IF NOT EXISTS idx_items_category ON items(category_id);
-- Индекс для выборки истории движения товара по дате (GET /items/{id}/movements)
CREATE INDEX IF NOT EXISTS idx_movements_item_date ON stock_movements(item_id, created_at DESC);
-- Частичный индекс для операции варианта: товары ниже минимального остатка
CREATE INDEX IF NOT EXISTS idx_items_below_min ON items(id) WHERE quantity < min_stock;
