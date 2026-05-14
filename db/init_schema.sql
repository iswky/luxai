CREATE SCHEMA IF NOT EXISTS r_luxai;

CREATE TABLE IF NOT EXISTS r_luxai.users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    pass_hash VARCHAR(255),
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    createdate TIMESTAMP DEFAULT NOW(),
    updatedate TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS r_luxai.tenders (
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

CREATE TABLE IF NOT EXISTS r_luxai.companies (
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

CREATE TABLE IF NOT EXISTS r_luxai.products (
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

CREATE TABLE IF NOT EXISTS r_luxai.tender_positions (
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

CREATE TABLE IF NOT EXISTS r_luxai.documents (
    id SERIAL PRIMARY KEY,
    tender_id BIGINT REFERENCES r_luxai.tenders(id) ON DELETE CASCADE,
    document BYTEA,
    createdate TIMESTAMP DEFAULT NOW(),
    updatedate TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS r_luxai.processing_queue (
    id SERIAL PRIMARY KEY,
    tender_number VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(1000),
    url TEXT,
    price VARCHAR(255),
    law VARCHAR(100),
    end_date VARCHAR(100),
    customer VARCHAR(500),
    first_seen VARCHAR(100),
    city VARCHAR(255),
    files_downloaded BOOLEAN DEFAULT FALSE,
    files_filtered BOOLEAN DEFAULT FALSE,
    files_parsed BOOLEAN DEFAULT FALSE,
    createdate TIMESTAMP DEFAULT NOW(),
    updatedate TIMESTAMP DEFAULT NOW()
);
