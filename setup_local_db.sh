#!/usr/bin/env bash

set -e
echo "=== Проверяю, что docker-compose.yml рядом ==="

if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Файл docker-compose.yml не найден."
    echo "Запусти скрипт из корня проекта, где лежит docker-compose.yml"
    exit 1
fi

echo "=== Поднимаю PostgreSQL через sudo docker compose ==="
sudo docker compose up -d db
echo "=== Жду запуск PostgreSQL ==="

until sudo docker exec postgres pg_isready -U user -d appdb >/dev/null 2>&1; do
    echo "Жду PostgreSQL..."
    sleep 2
done

echo "✅ PostgreSQL запущен"
echo "=== Создаю тестовую структуру БД ==="
sudo docker exec -i postgres psql -U user -d appdb <<'SQL'
CREATE SCHEMA IF NOT EXISTS r_luxai;

CREATE TABLE IF NOT EXISTS r_luxai.users (
    id SERIAL PRIMARY KEY,
    createby INTEGER,
    createdate TIMESTAMP DEFAULT NOW(),
    updateby INTEGER,
    updatedate TIMESTAMP DEFAULT NOW(),
    email VARCHAR(255) UNIQUE,
    pass_hash TEXT,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS r_luxai.companies (
    id SERIAL PRIMARY KEY,
    createby INTEGER,
    createdate TIMESTAMP DEFAULT NOW(),
    updateby INTEGER,
    updatedate TIMESTAMP DEFAULT NOW(),
    name VARCHAR(255) NOT NULL,
    country VARCHAR(100),
    counterparty_type VARCHAR(100),
    gisp TEXT,
    website TEXT,
    email VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS r_luxai.products (
    id SERIAL PRIMARY KEY,
    createby INTEGER,
    createdate TIMESTAMP DEFAULT NOW(),
    updateby INTEGER,
    updatedate TIMESTAMP DEFAULT NOW(),

    companies_id INTEGER REFERENCES r_luxai.companies(id),

    article VARCHAR(255),
    name VARCHAR(500),
    country VARCHAR(100),
    category VARCHAR(255),
    price NUMERIC(12, 2),
    stock_qty INTEGER,

    brand VARCHAR(255),
    model VARCHAR(255),
    release_year INTEGER,

    screen_size VARCHAR(100),
    cpu VARCHAR(255),
    cpu_cores INTEGER,
    gpu VARCHAR(255),
    ram_gb INTEGER,
    ram_type VARCHAR(100),
    storage_gb INTEGER,
    storage_type VARCHAR(100),
    os VARCHAR(255),

    print_speed_ppm INTEGER,
    warranty_months INTEGER,

    attributes JSONB DEFAULT '{}'::jsonb,
    last_update TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS r_luxai.tenders (
    id SERIAL PRIMARY KEY,
    createby INTEGER,
    createdate TIMESTAMP DEFAULT NOW(),
    updateby INTEGER,
    updatedate TIMESTAMP DEFAULT NOW(),

    tender_number VARCHAR(100) UNIQUE NOT NULL,
    published_at DATE,
    closing_date DATE,
    customer_name VARCHAR(500),
    total_budget NUMERIC(14, 2),
    status VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS r_luxai.tender_positions (
    id SERIAL PRIMARY KEY,
    createby INTEGER,
    createdate TIMESTAMP DEFAULT NOW(),
    updateby INTEGER,
    updatedate TIMESTAMP DEFAULT NOW(),

    tender_id INTEGER REFERENCES r_luxai.tenders(id) ON DELETE CASCADE,

    product_type VARCHAR(255),
    country VARCHAR(100),

    min_release_year INTEGER,
    screen_size VARCHAR(100),
    min_cpu VARCHAR(255),
    min_cpu_cores INTEGER,
    min_gpu VARCHAR(255),
    min_ram_gb INTEGER,
    ram_type VARCHAR(100),
    min_storage_gb INTEGER,
    storage_type VARCHAR(100),
    os VARCHAR(255),

    min_print_speed_ppm INTEGER,
    min_warranty_months INTEGER,

    attributes JSONB DEFAULT '{}'::jsonb,
    quantity INTEGER,
    max_price NUMERIC(12, 2)
);

CREATE TABLE IF NOT EXISTS r_luxai.tender_documents (
    id SERIAL PRIMARY KEY,
    tender_id INTEGER REFERENCES r_luxai.tenders(id) ON DELETE CASCADE,

    file_url TEXT,
    local_file TEXT,
    file_name VARCHAR(500),
    file_type VARCHAR(100),

    raw_text TEXT,
    parse_status VARCHAR(100) DEFAULT 'new',
    parse_error TEXT,

    createdate TIMESTAMP DEFAULT NOW(),
    updatedate TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS r_luxai.ai_parse_runs (
    id SERIAL PRIMARY KEY,
    tender_id INTEGER REFERENCES r_luxai.tenders(id) ON DELETE CASCADE,
    document_id INTEGER REFERENCES r_luxai.tender_documents(id) ON DELETE SET NULL,

    prompt TEXT,
    raw_response JSONB,
    status VARCHAR(100) DEFAULT 'new',
    error TEXT,

    createdate TIMESTAMP DEFAULT NOW(),
    updatedate TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS r_luxai.tender_position_matches (
    id SERIAL PRIMARY KEY,

    tender_position_id INTEGER REFERENCES r_luxai.tender_positions(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES r_luxai.products(id) ON DELETE CASCADE,
    company_id INTEGER REFERENCES r_luxai.companies(id) ON DELETE CASCADE,

    match_score NUMERIC(5, 2),
    price NUMERIC(12, 2),
    is_selected BOOLEAN DEFAULT FALSE,

    createdate TIMESTAMP DEFAULT NOW(),
    updatedate TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS r_luxai.contracts (
    id SERIAL PRIMARY KEY,
    tender_id INTEGER REFERENCES r_luxai.tenders(id) ON DELETE CASCADE,

    status VARCHAR(100) DEFAULT 'draft',
    document_file TEXT,
    html_content TEXT,

    createdate TIMESTAMP DEFAULT NOW(),
    updatedate TIMESTAMP DEFAULT NOW()
);
SQL

echo "✅ Таблицы созданы"

echo "=== Очищаю все старые данные ==="

sudo docker exec -i postgres psql -U user -d appdb <<'SQL'
TRUNCATE TABLE r_luxai.contracts RESTART IDENTITY CASCADE;
TRUNCATE TABLE r_luxai.tender_position_matches RESTART IDENTITY CASCADE;
TRUNCATE TABLE r_luxai.ai_parse_runs RESTART IDENTITY CASCADE;
TRUNCATE TABLE r_luxai.tender_documents RESTART IDENTITY CASCADE;
TRUNCATE TABLE r_luxai.tender_positions RESTART IDENTITY CASCADE;
TRUNCATE TABLE r_luxai.products RESTART IDENTITY CASCADE;
TRUNCATE TABLE r_luxai.tenders RESTART IDENTITY CASCADE;
TRUNCATE TABLE r_luxai.companies RESTART IDENTITY CASCADE;
TRUNCATE TABLE r_luxai.users RESTART IDENTITY CASCADE;
SQL

echo "✅ Все данные очищены"

echo "=== Проверяю количество данных ==="

sudo docker exec -i postgres psql -U user -d appdb <<'SQL'
SELECT 'companies' AS table_name, COUNT(*) FROM r_luxai.companies
UNION ALL
SELECT 'products' AS table_name, COUNT(*) FROM r_luxai.products
UNION ALL
SELECT 'tenders' AS table_name, COUNT(*) FROM r_luxai.tenders
UNION ALL
SELECT 'tender_positions' AS table_name, COUNT(*) FROM r_luxai.tender_positions;
SQL



echo ""
echo "✅ Готово!"
echo "Нажми Enter, чтобы внести тестовые данные..."
read -r
echo "=== Вношу тестовые данные ==="
# python3 load_parsed_tender.py
.venv/bin/python3 load_parsed_tender.py
echo "✅ Данные внесены"
echo "=== Проверяю количество данных ==="
sudo docker exec -i postgres psql -U user -d appdb <<'SQL'
SELECT 'companies' AS table_name, COUNT(*) FROM r_luxai.companies
UNION ALL
SELECT 'products' AS table_name, COUNT(*) FROM r_luxai.products
UNION ALL
SELECT 'tenders' AS table_name, COUNT(*) FROM r_luxai.tenders
UNION ALL
SELECT 'tender_positions' AS table_name, COUNT(*) FROM r_luxai.tender_positions;
SQL
echo ""
echo "✅ Готово!"
echo "Нажми Enter, чтобы закрыть скрипт..."
read -r
echo ""
echo "=== Останавливаю контейнеры ==="
sudo docker compose down
echo ""
echo "✅ Контейнеры остановлены."