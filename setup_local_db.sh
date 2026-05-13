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

echo "=== Создаю структуру БД r_luxai ==="

sudo docker exec -i postgres psql -U user -d appdb <<'SQL'
CREATE SCHEMA IF NOT EXISTS r_luxai;

DROP TABLE IF EXISTS r_luxai.documents CASCADE;
DROP TABLE IF EXISTS r_luxai.tender_positions CASCADE;
DROP TABLE IF EXISTS r_luxai.products CASCADE;
DROP TABLE IF EXISTS r_luxai.tenders CASCADE;
DROP TABLE IF EXISTS r_luxai.companies CASCADE;
DROP TABLE IF EXISTS r_luxai.users CASCADE;

CREATE TABLE r_luxai.users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    pass_hash VARCHAR(255),
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    createdate TIMESTAMP DEFAULT NOW(),
    updatedate TIMESTAMP DEFAULT NOW()
);

CREATE TABLE r_luxai.tenders (
    id SERIAL PRIMARY KEY,
    tender_number VARCHAR(100) UNIQUE NOT NULL,
    published_at TIMESTAMP,
    closing_date TIMESTAMP,
    customer_name VARCHAR(500),
    total_budget NUMERIC(14, 2),
    status VARCHAR(100) DEFAULT 'new',
    prompt TEXT,
    createdate TIMESTAMP DEFAULT NOW(),
    updatedate TIMESTAMP DEFAULT NOW()
);

CREATE TABLE r_luxai.companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    country VARCHAR(100),
    counterparty_type VARCHAR(100),
    gisp TEXT,
    website TEXT,
    email TEXT,
    createdate TIMESTAMP DEFAULT NOW(),
    updatedate TIMESTAMP DEFAULT NOW()
);

CREATE TABLE r_luxai.products (
    id SERIAL PRIMARY KEY,
    companies_id INTEGER REFERENCES r_luxai.companies(id) ON DELETE SET NULL,

    article VARCHAR(255),
    name VARCHAR(500) NOT NULL,
    country VARCHAR(100),
    category VARCHAR(255) NOT NULL,
    price NUMERIC(12, 2) NOT NULL,
    stock_qty INTEGER,

    brand VARCHAR(255),
    model VARCHAR(255),
    release_year SMALLINT,

    screen_size NUMERIC,
    cpu VARCHAR(255),
    cpu_cores BIGINT,
    gpu VARCHAR(255),
    ram_gb BIGINT,
    ram_type VARCHAR(100),
    storage_gb BIGINT,
    storage_type VARCHAR(100),
    os VARCHAR(255),

    print_speed_ppm SMALLINT,
    warranty_months SMALLINT,

    attributes JSONB DEFAULT '{}'::jsonb,
    last_update TIMESTAMP DEFAULT NOW()
);

CREATE TABLE r_luxai.tender_positions (
    id SERIAL PRIMARY KEY,
    tender_id INTEGER REFERENCES r_luxai.tenders(id) ON DELETE CASCADE,

    product_type VARCHAR(255),
    product_name VARCHAR(500),
    country VARCHAR(100),

    min_release_year SMALLINT,
    screen_size NUMERIC,
    min_ports_qty SMALLINT,

    min_cpu VARCHAR(255),
    min_cpu_cores BIGINT,
    min_gpu VARCHAR(255),
    min_ram_gb BIGINT,
    ram_type VARCHAR(100),
    min_storage_gb BIGINT,
    storage_type VARCHAR(100),
    os VARCHAR(255),

    min_print_speed_ppm SMALLINT,
    min_warranty_months SMALLINT,

    additional_info TEXT,
    components JSONB DEFAULT '[]'::jsonb,
    numerical_requirements JSON DEFAULT '{}'::json,
    string_and_bool_features JSON DEFAULT '{}'::json,
    grouped_features JSON DEFAULT '{}'::json,
    unparsed_features JSON DEFAULT '{}'::json,

    quantity INTEGER NOT NULL,
    max_price NUMERIC(12, 2)
);

CREATE TABLE r_luxai.documents (
    id SERIAL PRIMARY KEY,
    tender_id BIGINT REFERENCES r_luxai.tenders(id) ON DELETE CASCADE,
    document BYTEA,
    createdate TIMESTAMP DEFAULT NOW(),
    updatedate TIMESTAMP DEFAULT NOW()
);
SQL

echo "✅ Таблицы созданы"

echo "=== Проверяю количество данных ==="

sudo docker exec -i postgres psql -U user -d appdb <<'SQL'
SELECT 'users' AS table_name, COUNT(*) FROM r_luxai.users
UNION ALL
SELECT 'companies' AS table_name, COUNT(*) FROM r_luxai.companies
UNION ALL
SELECT 'products' AS table_name, COUNT(*) FROM r_luxai.products
UNION ALL
SELECT 'tenders' AS table_name, COUNT(*) FROM r_luxai.tenders
UNION ALL
SELECT 'tender_positions' AS table_name, COUNT(*) FROM r_luxai.tender_positions
UNION ALL
SELECT 'documents' AS table_name, COUNT(*) FROM r_luxai.documents;
SQL

echo ""
echo "✅ База создана и очищена."
echo ""
echo "Нажми Enter, чтобы внести данные из parsed_123.json через load_parsed_tender.py..."
read -r

echo "=== Проверяю наличие файлов ==="

if [ ! -f "load_parsed_tender.py" ]; then
    echo "❌ Не найден load_parsed_tender.py"
    echo "Он должен лежать в корне проекта рядом с setup_local_db.sh"
    exit 1
fi

if [ ! -f "parsed_123.json" ]; then
    echo "❌ Не найден parsed_123.json"
    echo "Он должен лежать в корне проекта рядом с setup_local_db.sh"
    exit 1
fi

if [ ! -f "123.pdf" ]; then
    echo "⚠️ Файл 123.pdf не найден."
    echo "Данные из JSON загрузятся, но PDF в таблицу documents не попадёт."
fi

echo "=== Вношу данные ==="

if [ -x "./.venv/bin/python" ]; then
    ./.venv/bin/python load_parsed_tender.py
elif [ -x "./backend/.venv/bin/python" ]; then
    ./backend/.venv/bin/python load_parsed_tender.py
else
    echo "❌ Не найден Python из виртуального окружения"
    echo "Проверенные пути:"
    echo "  ./.venv/bin/python"
    echo "  ./backend/.venv/bin/python"
    echo ""
    echo "Создай venv или установи зависимости:"
    echo "python3 -m venv .venv"
    echo "source .venv/bin/activate"
    echo "pip install -r requirements.txt"
    exit 1
fi

echo "=== Вношу тестовые компании и товары для сравнения ==="

sudo docker exec -i postgres psql -U user -d appdb <<'SQL'
INSERT INTO r_luxai.companies (
    name,
    country,
    counterparty_type,
    gisp,
    website,
    email
)
VALUES
    ('ООО "Интерактивные решения"', 'Россия', 'Поставщик', NULL, 'https://example.com/interactive', 'sales@interactive.example'),
    ('ООО "Учебные технологии"', 'Россия', 'Поставщик', NULL, 'https://example.com/edu-tech', 'sales@edu-tech.example'),
    ('АО "Цифровая школа"', 'Россия', 'Интегратор', NULL, 'https://example.com/digital-school', 'info@digital-school.example'),
    ('ООО "Лабораторное оборудование"', 'Россия', 'Поставщик', NULL, 'https://example.com/lab', 'sales@lab.example');

INSERT INTO r_luxai.products (
    companies_id,
    article,
    name,
    country,
    category,
    price,
    stock_qty,
    brand,
    model,
    release_year,
    screen_size,
    cpu,
    cpu_cores,
    gpu,
    ram_gb,
    ram_type,
    storage_gb,
    storage_type,
    os,
    print_speed_ppm,
    warranty_months,
    attributes
)
VALUES
    (
        1,
        'INT-FLOOR-001',
        'Интерактивный пол мобильный',
        'Россия',
        'Интерактивный пол',
        485000,
        3,
        'InteractivePro',
        'Floor M1',
        2025,
        NULL,
        '6-ядерный',
        6,
        NULL,
        8,
        'DDR4',
        240,
        'SSD',
        'Windows',
        NULL,
        24,
        '{"brightness_lm": "3000–4000 лм", "contrast": "30000:1–50000:1", "projection": "на пол"}'
    ),
    (
        1,
        'INT-WALL-001',
        'Интерактивная проекционная стена',
        'Россия',
        'Интерактивная проекционная стена',
        690000,
        2,
        'InteractivePro',
        'Wall S1',
        2025,
        NULL,
        '4-ядерный',
        4,
        NULL,
        8,
        'DDR4',
        240,
        'SSD',
        'Windows',
        NULL,
        24,
        '{"brightness_lm": "3000–4000 лм", "projection_length_m": "4.5–5 м", "projection_height_m": "2.5–3.1 м"}'
    ),
    (
        2,
        'LAB-NAT-001',
        'Цифровая лаборатория для школьников',
        'Россия',
        'Цифровая лаборатория',
        125000,
        10,
        'EduLab',
        'Natural Start',
        2025,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        'Windows, Android',
        NULL,
        12,
        '{"sensors": ["температура", "освещенность", "напряжение", "pH", "магнитное поле", "давление", "звук", "пульс"]}'
    ),
    (
        2,
        'LAB-BIO-008',
        'Цифровая лаборатория по биологии полевая',
        'Россия',
        'Цифровая лаборатория',
        148000,
        8,
        'EduLab',
        'Bio Field',
        2025,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        'Windows',
        NULL,
        12,
        '{"sensors": ["влажность", "освещенность", "pH", "электропроводность", "температура"], "includes": ["цифровой микроскоп", "электронные весы", "рюкзак"]}'
    ),
    (
        3,
        'PDD-COMPLEX-001',
        'Профессиональный мультимедийный интерактивный комплекс ПДД',
        'Россия',
        'Интерактивный комплекс',
        870000,
        1,
        'DigitalSchool',
        'PDD Pro',
        2025,
        23.6,
        'Intel Core i3',
        4,
        NULL,
        8,
        'DDR4',
        120,
        'SSD',
        'Windows',
        NULL,
        24,
        '{"touch_points": 10, "resolution": "1920x1080", "modules_count": 3}'
    ),
    (
        4,
        'GEO-KIT-001',
        'Комплект цифрового оборудования по географии',
        'Россия',
        'Цифровое оборудование',
        214000,
        5,
        'LabStore',
        'Geo Kit',
        2025,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        'Windows, Linux, Android',
        NULL,
        12,
        '{"sensors": ["температура", "магнитное поле", "pH", "давление", "расстояние", "электропроводность", "звук"]}'
    );
SQL
echo ""
echo "✅ Данные внесены"

echo "=== Проверяю количество данных после загрузки ==="

sudo docker exec -i postgres psql -U user -d appdb <<'SQL'
SELECT 'users' AS table_name, COUNT(*) FROM r_luxai.users
UNION ALL
SELECT 'companies' AS table_name, COUNT(*) FROM r_luxai.companies
UNION ALL
SELECT 'products' AS table_name, COUNT(*) FROM r_luxai.products
UNION ALL
SELECT 'tenders' AS table_name, COUNT(*) FROM r_luxai.tenders
UNION ALL
SELECT 'tender_positions' AS table_name, COUNT(*) FROM r_luxai.tender_positions
UNION ALL
SELECT 'documents' AS table_name, COUNT(*) FROM r_luxai.documents;
SQL

echo ""
echo "✅ Готово!"
echo ""
echo "Теперь можешь запускать Django в другом терминале:"
echo "python3 ./backend/manage.py runserver"
echo ""
echo "Проверяй:"
echo "http://127.0.0.1:8000/applications/"
echo "http://127.0.0.1:8000/applications/1/"
echo "http://127.0.0.1:8000/files/"
echo ""
echo "Когда закончишь тестировать, вернись сюда и нажми Enter."
read -r

echo ""
echo "=== Останавливаю контейнеры ==="
sudo docker compose down

echo ""
echo "✅ Контейнеры остановлены."