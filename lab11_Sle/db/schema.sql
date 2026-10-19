-- Лабораторная №11, вариант 17 «Склад». Схема реляционной БД (PostgreSQL)
DROP TABLE IF EXISTS stock_movements, item_suppliers, items, suppliers, categories CASCADE;

CREATE TABLE categories (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE suppliers (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(150) NOT NULL UNIQUE,
    phone       VARCHAR(30),
    city        VARCHAR(100) NOT NULL
);

-- 1:N  categories → items
CREATE TABLE items (
    id          SERIAL PRIMARY KEY,
    sku         VARCHAR(30)  NOT NULL UNIQUE,
    name        VARCHAR(200) NOT NULL CHECK (length(trim(name)) > 0),
    category_id INTEGER      NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    quantity    INTEGER      NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    min_stock   INTEGER      NOT NULL DEFAULT 0 CHECK (min_stock >= 0),
    price       NUMERIC(12,2) NOT NULL CHECK (price > 0),
    location    VARCHAR(20)  NOT NULL,
    image_url   VARCHAR(300)
);

-- N:M  items ↔ suppliers (промежуточная таблица с закупочной ценой)
CREATE TABLE item_suppliers (
    item_id        INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    supplier_id    INTEGER NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    purchase_price NUMERIC(12,2) NOT NULL CHECK (purchase_price > 0),
    PRIMARY KEY (item_id, supplier_id)
);

-- 1:N  items → stock_movements (журнал движения товара)
CREATE TABLE stock_movements (
    id            SERIAL PRIMARY KEY,
    item_id       INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    supplier_id   INTEGER REFERENCES suppliers(id) ON DELETE SET NULL,
    movement_type VARCHAR(3) NOT NULL CHECK (movement_type IN ('in', 'out')),
    quantity      INTEGER NOT NULL CHECK (quantity > 0),
    created_at    TIMESTAMP NOT NULL DEFAULT now()
);
