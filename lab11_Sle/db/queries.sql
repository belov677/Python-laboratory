-- 1. SELECT: все товары
SELECT * FROM items;

-- 2. WHERE: товары категории «канцелярия» (через подзапрос по имени категории)
SELECT sku, name, quantity FROM items
WHERE category_id = (SELECT id FROM categories WHERE name = 'канцелярия');

-- 3. ORDER BY: самые дорогие товары
SELECT sku, name, price FROM items ORDER BY price DESC LIMIT 5;

-- 4. JOIN: товары с названием категории
SELECT i.sku, i.name, c.name AS category FROM items i JOIN categories c ON c.id = i.category_id;

-- 5. LEFT JOIN: все поставщики и количество поставляемых ими товаров (включая 0)
SELECT s.name, COUNT(isup.item_id) AS items_count
FROM suppliers s LEFT JOIN item_suppliers isup ON isup.supplier_id = s.id
GROUP BY s.name ORDER BY items_count DESC;

-- 6. GROUP BY: количество позиций и единиц товара по категориям
SELECT c.name, COUNT(*) AS positions, SUM(i.quantity) AS units
FROM items i JOIN categories c ON c.id = i.category_id GROUP BY c.name;

-- 7. HAVING: категории, где стоимость запасов больше 100 000
SELECT c.name, SUM(i.quantity * i.price) AS stock_value
FROM items i JOIN categories c ON c.id = i.category_id
GROUP BY c.name HAVING SUM(i.quantity * i.price) > 100000;

-- 8. COUNT: число товаров ниже минимального остатка (операция варианта)
SELECT COUNT(*) FROM items WHERE quantity < min_stock;

-- 9. AVG / SUM: средняя цена и общая стоимость запасов
SELECT ROUND(AVG(price), 2) AS avg_price, SUM(quantity * price) AS total_value FROM items;

-- 10. INSERT: новый товар
INSERT INTO items(sku, name, category_id, quantity, min_stock, price, location)
VALUES ('CB-HDMI', 'Кабель HDMI 2 м', 1, 40, 10, 390, 'A-05');

-- 11. UPDATE: изменение цены и количества
UPDATE items SET price = 375, quantity = quantity + 10 WHERE sku = 'CB-HDMI';

-- 12. DELETE: удаление товара
DELETE FROM items WHERE sku = 'CB-HDMI';

-- 13. Подзапрос: товары дороже средней цены своей категории
SELECT i.sku, i.name, i.price FROM items i
WHERE i.price > (SELECT AVG(price) FROM items WHERE category_id = i.category_id);

-- 14. Несколько условий: электроника ниже минимального остатка или дороже 20 000
SELECT sku, name, quantity, min_stock, price FROM items
WHERE category_id = 1 AND (quantity < min_stock OR price > 20000);

-- 15. Связь нескольких таблиц: самый дешёвый поставщик для каждого товара
SELECT DISTINCT ON (i.id) i.sku, i.name, s.name AS supplier, isup.purchase_price
FROM items i
JOIN item_suppliers isup ON isup.item_id = i.id
JOIN suppliers s ON s.id = isup.supplier_id
ORDER BY i.id, isup.purchase_price;

-- 16. Оборот товара за сентябрь 2026: приход и расход
SELECT i.sku,
       SUM(CASE WHEN m.movement_type = 'in'  THEN m.quantity ELSE 0 END) AS received,
       SUM(CASE WHEN m.movement_type = 'out' THEN m.quantity ELSE 0 END) AS shipped
FROM stock_movements m JOIN items i ON i.id = m.item_id
WHERE m.created_at >= '2026-09-01' AND m.created_at < '2026-10-01'
GROUP BY i.sku ORDER BY i.sku;

-- 17. Транзакция: поступление товара (обе операции или ни одной)
BEGIN;
INSERT INTO stock_movements(item_id, supplier_id, movement_type, quantity) VALUES (2, 1, 'in', 15);
UPDATE items SET quantity = quantity + 15 WHERE id = 2;
COMMIT;
