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
echo "=== Создаю тестовую структуру БД и данные ==="
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

TRUNCATE TABLE r_luxai.tender_positions RESTART IDENTITY CASCADE;
TRUNCATE TABLE r_luxai.products RESTART IDENTITY CASCADE;
TRUNCATE TABLE r_luxai.tenders RESTART IDENTITY CASCADE;
TRUNCATE TABLE r_luxai.companies RESTART IDENTITY CASCADE;
TRUNCATE TABLE r_luxai.users RESTART IDENTITY CASCADE;

INSERT INTO r_luxai.users (
    email,
    pass_hash,
    full_name,
    is_active
)
VALUES (
    'admin@example.com',
    'test',
    'Тестовый админ',
    TRUE
);

INSERT INTO r_luxai.companies (
    name,
    country,
    counterparty_type,
    website,
    email
)
VALUES
    ('DNS', 'Россия', 'Поставщик', 'https://www.dns-shop.ru', 'info@dns-shop.ru'),
    ('Ситилинк', 'Россия', 'Поставщик', 'https://www.citilink.ru', 'info@citilink.ru'),
    ('Яндекс Маркет', 'Россия', 'Маркетплейс', 'https://market.yandex.ru', 'info@market.yandex.ru'),
    ('ServerMall', 'Россия', 'Поставщик серверов', 'https://example.com/servermall', 'sales@servermall.ru'),
    ('IT-Склад', 'Россия', 'Дистрибьютор', 'https://example.com/itsklad', 'sales@itsklad.ru'),
    ('Регард', 'Россия', 'Поставщик', 'https://www.regard.ru', 'info@regard.ru'),
    ('Комус', 'Россия', 'Поставщик', 'https://www.komus.ru', 'info@komus.ru');

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
    ram_gb,
    ram_type,
    storage_gb,
    storage_type,
    os,
    warranty_months
)
VALUES
    (
        1,
        'NB-LEN-E16-001',
        'Ноутбук Lenovo ThinkPad E16',
        'Китай',
        'Ноутбук',
        89990,
        12,
        'Lenovo',
        'ThinkPad E16',
        2024,
        '16"',
        'Intel Core i5',
        10,
        16,
        'DDR4',
        512,
        'SSD',
        'Windows 11 Pro',
        12
    ),
    (
        2,
        'NB-LEN-E16-002',
        'Lenovo ThinkPad E16 i5 16GB 512GB',
        'Китай',
        'Ноутбук',
        92400,
        8,
        'Lenovo',
        'ThinkPad E16',
        2024,
        '16"',
        'Intel Core i5',
        10,
        16,
        'DDR4',
        512,
        'SSD',
        'Windows 11 Pro',
        12
    ),
    (
        3,
        'MON-SAM-27-001',
        'Монитор Samsung 27 IPS',
        'Китай',
        'Монитор',
        21300,
        20,
        'Samsung',
        'S27',
        2023,
        '27"',
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        24
    ),
    (
        6,
        'MON-LG-27-002',
        'Монитор LG 27 Full HD IPS',
        'Китай',
        'Монитор',
        19990,
        14,
        'LG',
        '27MP',
        2023,
        '27"',
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        24
    ),
    (
        4,
        'SRV-DELL-R550',
        'Сервер Dell PowerEdge R550',
        'Китай',
        'Сервер',
        789000,
        3,
        'Dell',
        'PowerEdge R550',
        2024,
        NULL,
        'Intel Xeon Silver',
        16,
        128,
        'DDR4',
        2048,
        'SSD',
        NULL,
        36
    ),
    (
        5,
        'SRV-HP-DL380',
        'Сервер HP ProLiant DL380',
        'Китай',
        'Сервер',
        805500,
        2,
        'HP',
        'ProLiant DL380',
        2024,
        NULL,
        'Intel Xeon Silver',
        16,
        128,
        'DDR4',
        2048,
        'SSD',
        NULL,
        36
    ),
    (
        5,
        'SW-CISCO-48',
        'Коммутатор Cisco 48 портов',
        'Китай',
        'Коммутатор',
        176300,
        6,
        'Cisco',
        'Catalyst 48',
        2023,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        24
    ),
    (
        7,
        'MFP-HP-LJ-001',
        'МФУ HP LaserJet Pro',
        'Китай',
        'МФУ',
        41200,
        9,
        'HP',
        'LaserJet Pro',
        2023,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        12
    );

INSERT INTO r_luxai.tenders (
    tender_number,
    published_at,
    closing_date,
    customer_name,
    total_budget,
    status
)
VALUES
    (
        '03732000123',
        '2026-05-01',
        '2026-05-18',
        'ООО "Городские системы"',
        1850000,
        'Готово к разбору'
    ),
    (
        '01453000456',
        '2026-05-03',
        '2026-05-24',
        'АО "Инфраструктурные решения"',
        2420000,
        'Новая заявка'
    ),
    (
        '07889000991',
        '2026-05-05',
        '2026-05-30',
        'ГБУ "Центр цифрового развития"',
        970000,
        'На проверке'
    );

INSERT INTO r_luxai.tender_positions (
    tender_id,
    product_type,
    country,
    min_cpu,
    min_cpu_cores,
    min_ram_gb,
    ram_type,
    min_storage_gb,
    storage_type,
    os,
    quantity,
    max_price,
    attributes
)
VALUES
    (
        1,
        'Ноутбук',
        'Китай',
        'Intel Core i5',
        8,
        16,
        'DDR4',
        512,
        'SSD',
        'Windows 11 Pro',
        10,
        95000,
        '{"screen": "16 дюймов"}'
    ),
    (
        1,
        'Монитор',
        'Китай',
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        10,
        23000,
        '{"screen": "27 дюймов", "matrix": "IPS", "resolution": "Full HD"}'
    ),
    (
        1,
        'МФУ',
        'Китай',
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        3,
        42000,
        '{"type": "laser", "format": "A4", "network": true}'
    ),
    (
        2,
        'Сервер',
        'Китай',
        'Intel Xeon Silver',
        12,
        128,
        'DDR4',
        2048,
        'SSD',
        NULL,
        2,
        820000,
        '{"form_factor": "2U", "raid": true}'
    ),
    (
        2,
        'Коммутатор',
        'Китай',
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        4,
        185000,
        '{"ports": "48x1G RJ-45", "sfp": "4x10G SFP+"}'
    );
SQL

echo "✅ Таблицы и тестовые данные созданы"
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
echo ""
echo "Нажми Enter, чтобы закрыть скрипт..."
read -r
echo ""
echo "=== Останавливаю контейнеры ==="
sudo docker compose down
echo ""
echo "✅ Контейнеры остановлены."