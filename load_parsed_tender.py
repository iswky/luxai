import json
import psycopg2
from psycopg2.extras import Json


DB_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "dbname": "appdb",
    "user": "user",
    "password": "pass",
}


def to_int(value, default=1):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def main():
    with open("parsed_123.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    tender_number = "TEST-123-PDF"
    title = data.get("title", "Без названия")
    items = data.get("items", [])

    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            # 1. Создаём или обновляем тендер
            cur.execute(
                """
                INSERT INTO r_luxai.tenders (
                    tender_number,
                    published_at,
                    closing_date,
                    customer_name,
                    total_budget,
                    status
                )
                VALUES (
                    %s,
                    CURRENT_DATE,
                    NULL,
                    %s,
                    NULL,
                    %s
                )
                ON CONFLICT (tender_number)
                DO UPDATE SET
                    customer_name = EXCLUDED.customer_name,
                    status = EXCLUDED.status,
                    updatedate = NOW()
                RETURNING id;
                """,
                [
                    tender_number,
                    "Тестовый заказчик из PDF",
                    "AI разобрал заявку",
                ],
            )

            tender_id = cur.fetchone()[0]

            # 2. Чистим старые позиции этого тендера,
            # чтобы при повторном запуске не было дублей
            cur.execute(
                """
                DELETE FROM r_luxai.tender_positions
                WHERE tender_id = %s;
                """,
                [tender_id],
            )

            # 3. Кладём позиции из JSON в tender_positions
            for item in items:
                attrs = {
                    "source_file": data.get("source_file"),
                    "document_title": title,
                    "position_number": item.get("position_number"),
                    "name": item.get("name"),
                    "category": item.get("category"),
                    "requirements_summary": item.get("requirements_summary"),
                    "key_requirements": item.get("key_requirements", {}),
                }

                key_requirements = item.get("key_requirements", {})

                cur.execute(
                    """
                    INSERT INTO r_luxai.tender_positions (
                        tender_id,
                        product_type,
                        country,
                        min_release_year,
                        screen_size,
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
                        attributes,
                        quantity,
                        max_price
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    );
                    """,
                    [
                        tender_id,
                        item.get("product_type") or item.get("name"),
                        key_requirements.get("country"),
                        key_requirements.get("min_release_year"),
                        key_requirements.get("screen_size"),
                        key_requirements.get("cpu_min") or key_requirements.get("cpu_type"),
                        key_requirements.get("cpu_cores_min"),
                        key_requirements.get("gpu_min"),
                        key_requirements.get("ram_min_gb"),
                        key_requirements.get("ram_type"),
                        key_requirements.get("ssd_min_gb") or key_requirements.get("storage_min_gb"),
                        key_requirements.get("storage_type"),
                        key_requirements.get("os"),
                        key_requirements.get("print_speed_ppm_min"),
                        key_requirements.get("warranty_months_min"),
                        Json(attrs),
                        to_int(item.get("quantity"), 1),
                        None,
                    ],
                )

        conn.commit()

    print(f"✅ Загружено в БД: тендер id={tender_id}, позиций={len(items)}")


if __name__ == "__main__":
    main()
