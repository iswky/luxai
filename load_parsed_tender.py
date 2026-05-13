import json
from pathlib import Path

import psycopg2
from psycopg2.extras import Json


DB_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "dbname": "appdb",
    "user": "user",
    "password": "pass",
}


JSON_PATH = Path("parsed_123.json")
PDF_PATH = Path("123.pdf")


DEFAULT_PROMPT = """
Проанализируй документ закупки.
Извлеки позиции закупки, количество, единицы измерения, характеристики,
комплектацию, числовые требования и дополнительные условия.
Верни результат строго в JSON.
""".strip()


def to_int(value, default=1):
    if value is None:
        return default

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def to_numeric_or_none(value):
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_range_value(value):
    if value is None:
        return None

    return str(value).strip()


# we decompose key_requirements from json into the new database structure: - numerical_requirements: numeric and range params - string_and_bool_features: strings and boolean - components: lists of equipment/sensors/funcs - grouped_features: grouping by source blocks - unparsed_features: everything original without loss
def split_requirements(key_requirements):

    numerical = {}
    string_bool = {}
    components = []
    grouped = {}
    unparsed = {}

    numerical_keys = {
        "touch_points_min",
        "ram_min_gb",
        "storage_min_gb",
        "ssd_min_gb",
        "tablet_ram_min_gb",
        "tablet_storage_min_gb",
        "tablet_battery_min_mah",
        "tablet_screen_min_inches",
        "cpu_frequency_min_ghz",
        "camera_scan_rate_min_fps",
        "brightness_lm",
        "hdmi_ports_min",
        "usb_cables_min",
        "quiz_questions_min",
        "multitouch_points_min",
        "container_rack_min",
        "projection_length_m",
        "projection_height_m",
        "projection_width_m",
        "height_mm",
        "floor_cover_area_m2",
        "modules_count",
    }

    component_keys = {
        "sensors",
        "software_sections",
        "software_features",
        "wifi_standards",
    }

    for key, value in key_requirements.items():
        unparsed[key] = value

        if key in component_keys and isinstance(value, list):
            grouped[key] = value

            for item in value:
                components.append({
                    "group": key,
                    "name": item,
                })

        elif key in numerical_keys:
            numerical[key] = normalize_range_value(value)

        else:
            string_bool[key] = value

    return {
        "components": components,
        "numerical_requirements": numerical,
        "string_and_bool_features": string_bool,
        "grouped_features": grouped,
        "unparsed_features": unparsed,
    }


def extract_position_columns(item):
    key = item.get("key_requirements") or {}

    return {
        "country": key.get("country"),
        "min_release_year": key.get("min_release_year"),
        "screen_size": (
            key.get("screen_size")
            or key.get("tablet_screen_min_inches")
        ),
        "min_ports_qty": key.get("min_ports_qty"),

        "min_cpu": (
            key.get("cpu_min")
            or key.get("cpu_type")
        ),
        "min_cpu_cores": key.get("cpu_cores_min"),
        "min_gpu": key.get("gpu_min"),

        "min_ram_gb": (
            key.get("ram_min_gb")
            or key.get("tablet_ram_min_gb")
        ),
        "ram_type": key.get("ram_type"),

        "min_storage_gb": (
            key.get("ssd_min_gb")
            or key.get("storage_min_gb")
            or key.get("tablet_storage_min_gb")
        ),
        "storage_type": key.get("storage_type"),
        "os": key.get("os"),

        "min_print_speed_ppm": key.get("print_speed_ppm_min"),
        "min_warranty_months": key.get("warranty_months_min"),
    }


def main():
    if not JSON_PATH.exists():
        raise FileNotFoundError(f"Не найден файл {JSON_PATH}")

    with JSON_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    tender_number = "TEST-123-PDF"
    title = data.get("title") or "Описание объекта закупки"
    items = data.get("items", [])

    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO r_luxai.tenders (
                    tender_number,
                    published_at,
                    closing_date,
                    customer_name,
                    total_budget,
                    status,
                    prompt
                )
                VALUES (
                    %s,
                    NOW(),
                    NULL,
                    %s,
                    NULL,
                    %s,
                    %s
                )
                ON CONFLICT (tender_number)
                DO UPDATE SET
                    customer_name = EXCLUDED.customer_name,
                    status = EXCLUDED.status,
                    prompt = EXCLUDED.prompt,
                    updatedate = NOW()
                RETURNING id;
                """,
                [
                    tender_number,
                    "Тестовый заказчик из PDF",
                    "AI разобрал заявку",
                    DEFAULT_PROMPT,
                ],
            )

            tender_id = cur.fetchone()[0]

            cur.execute(
                """
                DELETE FROM r_luxai.documents
                WHERE tender_id = %s;
                """,
                [tender_id],
            )

            cur.execute(
                """
                DELETE FROM r_luxai.tender_positions
                WHERE tender_id = %s;
                """,
                [tender_id],
            )

            if PDF_PATH.exists():
                pdf_bytes = PDF_PATH.read_bytes()

                cur.execute(
                    """
                    INSERT INTO r_luxai.documents (
                        tender_id,
                        document
                    )
                    VALUES (%s, %s);
                    """,
                    [
                        tender_id,
                        psycopg2.Binary(pdf_bytes),
                    ],
                )

            for item in items:
                key_requirements = item.get("key_requirements") or {}
                split = split_requirements(key_requirements)
                columns = extract_position_columns(item)

                additional_info = item.get("requirements_summary") or ""

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
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s,
                        %s, %s, %s, %s, %s, %s,
                        %s, %s
                    );
                    """,
                    [
                        tender_id,
                        item.get("product_type"),
                        item.get("name"),
                        columns["country"],

                        columns["min_release_year"],
                        to_numeric_or_none(columns["screen_size"]),
                        columns["min_ports_qty"],

                        columns["min_cpu"],
                        columns["min_cpu_cores"],
                        columns["min_gpu"],
                        columns["min_ram_gb"],
                        columns["ram_type"],
                        columns["min_storage_gb"],
                        columns["storage_type"],
                        columns["os"],

                        columns["min_print_speed_ppm"],
                        columns["min_warranty_months"],

                        additional_info,
                        Json(split["components"]),
                        Json(split["numerical_requirements"]),
                        Json(split["string_and_bool_features"]),
                        Json(split["grouped_features"]),
                        Json(split["unparsed_features"]),

                        to_int(item.get("quantity"), 1),
                        None,
                    ],
                )

        conn.commit()

    print(f"Loaded into DB: tender id={tender_id}, positions={len(items)}")


if __name__ == "__main__":
    main()