"""
db.py
--------------------
Работа с PostgreSQL: запись распарсенных тендеров и удаление дублей.

Параметры подключения соответствуют docker-compose.yml:
    db:
      image: postgres:15
      environment:
        POSTGRES_DB: appdb
        POSTGRES_USER: user
        POSTGRES_PASSWORD: pass
      ports:
        - "5432:5432"

Схема r_luxai (актуальная):
  tenders(id, tender_number UNIQUE, customer_name, status, prompt, ...)
  tender_positions(tender_id, product_type, product_name, country,
                   min_release_year, screen_size, min_ports_qty, min_cpu,
                   min_cpu_cores, min_gpu, min_ram_gb, ram_type,
                   min_storage_gb, storage_type, os, min_print_speed_ppm,
                   min_warranty_months, additional_info,
                   components jsonb,
                   numerical_requirements json,
                   string_and_bool_features json,
                   grouped_features json,
                   unparsed_features json,
                   quantity, max_price)
"""

from typing import Any, Dict, List, Optional, Tuple
import logging
import re

import psycopg2
from psycopg2.extras import Json


logger = logging.getLogger(__name__)

DB_CONFIG: Dict[str, str] = {
    "host": "localhost",
    "port": "5432",
    "dbname": "appdb",
    "user": "user",
    "password": "pass",
}

# Лимиты длины varchar-колонок (из дампа). Если LLM вернёт длиннее — обрежем.
PRODUCT_TYPE_MAXLEN = 50
PRODUCT_NAME_MAXLEN = 50
COUNTRY_MAXLEN = 50
CPU_MAXLEN = 100
GPU_MAXLEN = 100
RAM_TYPE_MAXLEN = 10
STORAGE_TYPE_MAXLEN = 10
OS_MAXLEN = 50


# ─────────────────────── маппинг ключей JSON → типизированные колонки ───────────────────────
# В numerical_requirements / string_and_bool_features ключи свободные, на русском.
# Эти regex выцепляют то, что укладывается в отдельные колонки tender_positions
# для последующего быстрого SQL-сравнения с products.
# Все остальные ключи никуда не теряются — они ложатся в одноимённые json-колонки целиком.

NUMERIC_KEY_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("min_release_year",    re.compile(r"^(год_выпуска|release_year)", re.IGNORECASE)),
    ("screen_size",         re.compile(r"^(диагональ_экрана_дюйм|screen_size|диагональ)", re.IGNORECASE)),
    ("min_ports_qty",       re.compile(r"^(количество_портов|порты_шт|ports_qty)", re.IGNORECASE)),
    ("min_cpu_cores",       re.compile(r"^(количество_ядер|cpu_cores|ядра_процессора)", re.IGNORECASE)),
    ("min_ram_gb",          re.compile(r"^(оперативная_память_гб|ram_gb|озу_гб)", re.IGNORECASE)),
    ("min_storage_gb",      re.compile(r"^(память_гб|storage_gb|диск_гб|ssd_гб|hdd_гб|объем_накопителя_гб)", re.IGNORECASE)),
    ("min_print_speed_ppm", re.compile(r"^(скорость_печати_стр_мин|print_speed_ppm|скорость_печати)", re.IGNORECASE)),
    ("min_warranty_months", re.compile(r"^(гарантия_месяцев|warranty_months|гарантия_мес)", re.IGNORECASE)),
]

STRING_KEY_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("country",      re.compile(r"^(страна_производства|country|страна)", re.IGNORECASE)),
    ("min_cpu",      re.compile(r"^(процессор|cpu|тип_процессора)", re.IGNORECASE)),
    ("min_gpu",      re.compile(r"^(видеокарта|gpu|графический_процессор)", re.IGNORECASE)),
    ("ram_type",     re.compile(r"^(тип_оперативной_памяти|ram_type|тип_озу)", re.IGNORECASE)),
    ("storage_type", re.compile(r"^(тип_накопителя|storage_type|тип_диска)", re.IGNORECASE)),
    ("os",           re.compile(r"^(операционная_система|os|ос)", re.IGNORECASE)),
]


def _extract_number_value(value: Any) -> Optional[float]:
    """Из { gte: X } / { lte: X } / { eq: X } / числа → достаём число (приоритет: gte > eq > lte)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        for key in ("gte", "eq", "lte"):
            if key in value and isinstance(value[key], (int, float)):
                return float(value[key])
    return None


def _find_typed_columns(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Пробегает по numerical_requirements / string_and_bool_features и пытается уложить
    значения в типизированные колонки tender_positions.

    Возвращает dict {colname: value}.
    """
    columns: Dict[str, Any] = {}

    for key, val in (item.get("numerical_requirements") or {}).items():
        number = _extract_number_value(val)
        if number is None:
            continue
        for colname, pattern in NUMERIC_KEY_PATTERNS:
            if pattern.search(key):
                columns[colname] = number
                break

    for key, val in (item.get("string_and_bool_features") or {}).items():
        if not isinstance(val, str):
            continue
        for colname, pattern in STRING_KEY_PATTERNS:
            if pattern.search(key):
                columns[colname] = val
                break

    return columns


def _to_int(value: Any, default: int = 1) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _truncate(value: Optional[str], maxlen: int) -> Optional[str]:
    """Обрезает строку до maxlen символов (varchar не примет длиннее)."""
    if value is None:
        return None
    s = str(value)
    return s[:maxlen] if len(s) > maxlen else s


# ─────────────────────── публичные функции ───────────────────────

def save_tender_to_db(
    tender_number: str,
    parsed_json: Dict[str, Any],
    pdf_source_file: Optional[str] = None,
    customer_name: Optional[str] = None,
    prompt: Optional[str] = None,
) -> Optional[int]:
    """
    Сохраняет распарсенный тендер в БД.

    Поведение при дубле (tender_number уже есть):
      - тендер UPDATE'ится (updatedate = now())
      - его старые tender_positions удаляются
      - вставляются новые позиции из parsed_json
    Всё в одной транзакции.

    Args:
        tender_number: номер тендера (из колонки 1 Excel)
        parsed_json: то, что возвращает parse_pdf_to_json(...). Ожидается ключ "items".
        pdf_source_file: имя исходного pdf-файла (пойдёт в additional_info)
        customer_name: имя заказчика
        prompt: текст промпта, который слали в LLM (опционально)

    Returns:
        id тендера в БД либо None при ошибке.
    """
    items: List[Dict[str, Any]] = parsed_json.get("items", []) or []

    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                # 1. UPSERT тендера
                cur.execute(
                    """
                    INSERT INTO r_luxai.tenders (
                        tender_number, customer_name, status, prompt
                    ) VALUES (
                        %s, %s, %s, %s
                    )
                    ON CONFLICT (tender_number) DO UPDATE SET
                        customer_name = COALESCE(EXCLUDED.customer_name, r_luxai.tenders.customer_name),
                        prompt = COALESCE(EXCLUDED.prompt, r_luxai.tenders.prompt),
                        updatedate = NOW()
                    RETURNING id;
                    """,
                    [tender_number, customer_name, "parsed", prompt],
                )
                tender_id = cur.fetchone()[0]

                # 2. Сносим старые позиции (на случай повторного запуска)
                cur.execute(
                    "DELETE FROM r_luxai.tender_positions WHERE tender_id = %s;",
                    [tender_id],
                )

                # 3. Льём новые позиции
                inserted = 0
                for item in items:
                    cols = _find_typed_columns(item)

                    additional_info_parts = []
                    if pdf_source_file:
                        additional_info_parts.append(f"source_file={pdf_source_file}")
                    if item.get("_source_pdf"):
                        additional_info_parts.append(f"pdf={item['_source_pdf']}")
                    additional_info = "; ".join(additional_info_parts) or None

                    cur.execute(
                        """
                        INSERT INTO r_luxai.tender_positions (
                            tender_id,
                            product_type,
                            product_name,
                            country,
                            min_release_year,
                            screen_size,
                            min_ports_qty,
                            min_cpu,
                            min_cpu_cores,
                            min_gpu,
                            min_ram_gb,
                            ram_type,
                            min_storage_gb,
                            storage_type,
                            os,
                            min_print_speed_ppm,
                            min_warranty_months,
                            additional_info,
                            components,
                            numerical_requirements,
                            string_and_bool_features,
                            grouped_features,
                            unparsed_features,
                            quantity,
                            max_price
                        )
                        VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        );
                        """,
                        [
                            tender_id,
                            _truncate(item.get("product_type"), PRODUCT_TYPE_MAXLEN),
                            _truncate(item.get("product_name"), PRODUCT_NAME_MAXLEN),
                            _truncate(cols.get("country"), COUNTRY_MAXLEN),
                            cols.get("min_release_year"),
                            cols.get("screen_size"),
                            cols.get("min_ports_qty"),
                            _truncate(cols.get("min_cpu"), CPU_MAXLEN),
                            cols.get("min_cpu_cores"),
                            _truncate(cols.get("min_gpu"), GPU_MAXLEN),
                            cols.get("min_ram_gb"),
                            _truncate(cols.get("ram_type"), RAM_TYPE_MAXLEN),
                            cols.get("min_storage_gb"),
                            _truncate(cols.get("storage_type"), STORAGE_TYPE_MAXLEN),
                            _truncate(cols.get("os"), OS_MAXLEN),
                            cols.get("min_print_speed_ppm"),
                            cols.get("min_warranty_months"),
                            additional_info,
                            Json(item.get("components") or []),
                            Json(item.get("numerical_requirements") or {}),
                            Json(item.get("string_and_bool_features") or {}),
                            Json(item.get("grouped_features") or {}),
                            Json(item.get("unparsed_features") or []),
                            _to_int(item.get("quantity"), 1),
                            None,
                        ],
                    )
                    inserted += 1

            conn.commit()
            logger.info(
                f"✅ Тендер {tender_number} (db id={tender_id}) записан, позиций: {inserted}"
            )
            return tender_id

    except psycopg2.Error as e:
        logger.error(f"❌ Ошибка PostgreSQL при сохранении тендера {tender_number}: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Непредвиденная ошибка при сохранении тендера {tender_number}: {e}")
        return None


def delete_tender_from_db(tender_number: str) -> bool:
    """
    Удаляет тендер и все его позиции из БД по tender_number.
    Возвращает True, если что-то реально удалилось.
    """
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM r_luxai.tender_positions
                    WHERE tender_id IN (
                        SELECT id FROM r_luxai.tenders WHERE tender_number = %s
                    );
                    """,
                    [tender_number],
                )
                cur.execute(
                    "DELETE FROM r_luxai.tenders WHERE tender_number = %s RETURNING id;",
                    [tender_number],
                )
                deleted = cur.fetchone()
            conn.commit()
            if deleted:
                logger.info(f"🗑 Тендер {tender_number} удалён из БД (id={deleted[0]})")
                return True
            return False
    except psycopg2.Error as e:
        logger.error(f"❌ Ошибка PostgreSQL при удалении тендера {tender_number}: {e}")
        return False


def deduplicate_tenders_in_db() -> int:
    """
    Чистит дубли в r_luxai.tenders. Уникальный ключ (tender_number) на таблице есть,
    поэтому строгих дублей быть не должно. Но если по какой-то причине вставка
    шла раньше без UPSERT'а и они появились — оставляем самую свежую запись
    (по createdate / id), остальные сносим вместе с их позициями.

    Returns:
        количество удалённых строк-дублей.
    """
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    WITH ranked AS (
                        SELECT
                            id,
                            tender_number,
                            ROW_NUMBER() OVER (
                                PARTITION BY tender_number
                                ORDER BY createdate DESC NULLS LAST, id DESC
                            ) AS rn
                        FROM r_luxai.tenders
                    )
                    SELECT id FROM ranked WHERE rn > 1;
                    """
                )
                dup_ids = [row[0] for row in cur.fetchall()]

                if not dup_ids:
                    logger.info("✅ Дублей в r_luxai.tenders не найдено")
                    return 0

                cur.execute(
                    "DELETE FROM r_luxai.tender_positions WHERE tender_id = ANY(%s);",
                    [dup_ids],
                )
                cur.execute(
                    "DELETE FROM r_luxai.tenders WHERE id = ANY(%s);",
                    [dup_ids],
                )
            conn.commit()
            logger.info(f"🗑 Удалено дублей тендеров в БД: {len(dup_ids)}")
            return len(dup_ids)
    except psycopg2.Error as e:
        logger.error(f"❌ Ошибка PostgreSQL при дедупликации: {e}")
        return 0