from .db import get_connection

from .cities import RUSSIAN_CITIES


def db_column_exists(table_name, column_name, schema_name='r_luxai'):
    """Check DB columns so old dumps keep working before migration."""
    query = """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = %s
          AND table_name = %s
          AND column_name = %s
        LIMIT 1;
    """

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, [schema_name, table_name, column_name])
                return cur.fetchone() is not None
    except Exception:
        return False


def documents_have_file_metadata():
    return db_column_exists('documents', 'document_path')


def document_metadata_select(alias='d'):
    if documents_have_file_metadata():
        return f'{alias}.document_path, {alias}.filename'

    return 'NULL::text AS document_path, NULL::text AS filename'


def application_file_url(application_id):
    return f'/applications/{application_id}/file/'


def document_file_url(document_id):
    return f'/files/{document_id}/open/'


def fetch_files():
    query = f"""
        SELECT
            d.id,
            d.tender_id,
            {document_metadata_select('d')},
            t.tender_number,
            t.customer_name,
            t.status,
            t.prompt,
            pq.city,
            d.createdate
        FROM r_luxai.documents d
        JOIN r_luxai.tenders t ON t.id = d.tender_id
        LEFT JOIN r_luxai.processing_queue pq ON pq.tender_number = t.tender_number
        ORDER BY d.createdate DESC;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

    files = []

    for row in rows:
        filename = row.get('filename') or f"{row['tender_number']}.pdf"

        files.append({
            'id': row['id'],
            'name': filename,
            'source': 'Госзакупки',
            'status': row['status'] or 'Новая',
            'confidence': '-',
            'comment': row['customer_name'] or '',
            'city': row.get('city') or 'Не указан',
            'parse_prompt': row.get('prompt') or 'Промпт не задан',
            'application_file': document_file_url(row['id']),
        })

    return files


def fetch_equipment():
    query = """
        SELECT
            p.id,
            p.name AS item,
            p.category,
            p.price,
            p.stock_qty,
            c.name AS supplier
        FROM r_luxai.products p
        LEFT JOIN r_luxai.companies c ON c.id = p.companies_id
        ORDER BY p.id DESC
        LIMIT 50;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

    equipment = []

    for row in rows:
        equipment.append({
            'id': row['id'],
            'supplier': row['supplier'] or 'Не указан',
            'item': row['item'] or 'Без названия',
            'category': row['category'] or 'Без категории',
            'application_file': '/static/webui/files/application_form.pdf',
        })

    return equipment


# def fetch_available_cities():
#     query = """
#         SELECT DISTINCT city
#         FROM r_luxai.processing_queue
#         WHERE city IS NOT NULL
#           AND city <> ''
#           AND city <> 'Не указан'
#         ORDER BY city;
#     """

#     with get_connection() as conn:
#         with conn.cursor() as cur:
#             cur.execute(query)
#             rows = cur.fetchall()

#     return [row['city'] for row in rows]

def fetch_available_cities():
    return list(RUSSIAN_CITIES)


def fetch_applications(filters=None):
    filters = filters or {}

    query = """
        SELECT
            t.id,
            t.tender_number,
            t.customer_name,
            t.closing_date,
            t.total_budget,
            t.status,
            pq.city,
            COUNT(tp.id) AS positions_count
        FROM r_luxai.tenders t
        LEFT JOIN r_luxai.tender_positions tp ON tp.tender_id = t.id
        LEFT JOIN r_luxai.processing_queue pq ON pq.tender_number = t.tender_number
        WHERE 1 = 1
    """

    params = []

    date_from = filters.get('date_from')
    date_to = filters.get('date_to')
    status = filters.get('status')
    price_from = filters.get('price_from')
    price_to = filters.get('price_to')
    city = filters.get('city')

    if date_from:
        query += " AND t.closing_date >= %s"
        params.append(date_from)

    if date_to:
        query += " AND t.closing_date <= %s"
        params.append(date_to)

    if status:
        query += " AND t.status = %s"
        params.append(status)

    if price_from:
        query += " AND t.total_budget >= %s"
        params.append(price_from)

    if price_to:
        query += " AND t.total_budget <= %s"
        params.append(price_to)

    # if city:
    #     query += " AND pq.city = %s"
    #     params.append(city)

    if city:
        query += " AND pq.city ILIKE %s"
        params.append(f"%{city}%")

    query += """
        GROUP BY
            t.id,
            t.tender_number,
            t.customer_name,
            t.closing_date,
            t.total_budget,
            t.status,
            t.createdate,
            pq.city
        ORDER BY t.createdate DESC;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

    applications = []

    for row in rows:
        applications.append({
            'id': row['id'],
            'title': f"Тендер {row['tender_number']}",
            'number': row['tender_number'],
            'customer': row['customer_name'] or 'Не указан',
            'city': row.get('city') or 'Не указан',
            'deadline': format_date(row['closing_date']),
            'price': format_money(row['total_budget']),
            'status': row['status'] or 'Новая',
            'file': application_file_url(row['id']),
            'items': [None] * int(row['positions_count'] or 0),
        })

    return applications


def fetch_application_detail(application_id):
    tender_query = """
        SELECT
            t.id,
            t.tender_number,
            t.customer_name,
            t.closing_date,
            t.total_budget,
            t.status,
            t.prompt,
            pq.city
        FROM r_luxai.tenders t
        LEFT JOIN r_luxai.processing_queue pq ON pq.tender_number = t.tender_number
        WHERE t.id = %s;
    """

    positions_query = """
        SELECT
            id,
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
        FROM r_luxai.tender_positions
        WHERE tender_id = %s
        ORDER BY id;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(tender_query, [application_id])
            tender = cur.fetchone()

            if not tender:
                return None

            cur.execute(positions_query, [application_id])
            positions = cur.fetchall()

    application = {
        'id': tender['id'],
        'title': f"Тендер {tender['tender_number']}",
        'number': tender['tender_number'],
        'customer': tender['customer_name'] or 'Не указан',
        'city': tender.get('city') or 'Не указан',
        'deadline': format_date(tender['closing_date']),
        'price': format_money(tender['total_budget']),
        'status': tender['status'] or 'Новая',
        'prompt': tender.get('prompt') or '',
        'file': application_file_url(tender['id']),
        'items': [],
    }

    for index, position in enumerate(positions, start=1):
        unparsed = position.get('unparsed_features') or {}
        numerical = position.get('numerical_requirements') or {}
        string_bool = position.get('string_and_bool_features') or {}
        grouped = position.get('grouped_features') or {}
        components = position.get('components') or []

        merged_requirements = {}
        merged_requirements.update(string_bool)
        merged_requirements.update(numerical)
        merged_requirements.update(grouped)

        item = {
            'id': position['id'],
            'position_number': index,
            'name': (
                position.get('product_name')
                or unparsed.get('name')
                or position.get('product_type')
                or 'Позиция без названия'
            ),
            'product_type': position.get('product_type') or 'Без типа',
            'category': unparsed.get('category') or position.get('product_type') or 'Без категории',
            'quantity': format_quantity(position.get('quantity')),
            'unit': unparsed.get('unit') or 'шт',
            'requirements': position.get('additional_info') or 'Описание отсутствует',
            'components': normalize_components(components),
            'key_requirements': normalize_key_requirements(merged_requirements),
            'budget': format_money(position.get('max_price')),
            'shops': fetch_shops_for_position(position),
        }

        application['items'].append(item)

    return application


def fetch_document_file(document_id):
    query = f"""
        SELECT
            d.id,
            d.tender_id,
            d.document,
            {document_metadata_select('d')},
            t.tender_number
        FROM r_luxai.documents d
        JOIN r_luxai.tenders t ON t.id = d.tender_id
        WHERE d.id = %s;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, [document_id])
            return cur.fetchone()


def fetch_application_file(application_id):
    query = f"""
        SELECT
            t.id AS tender_id,
            t.tender_number,
            d.id AS document_id,
            d.document,
            {document_metadata_select('d')}
        FROM r_luxai.tenders t
        LEFT JOIN LATERAL (
            SELECT *
            FROM r_luxai.documents
            WHERE tender_id = t.id
            ORDER BY createdate DESC NULLS LAST, id DESC
            LIMIT 1
        ) d ON TRUE
        WHERE t.id = %s;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, [application_id])
            return cur.fetchone()


def fetch_shops_for_position(position):
    query = """
        SELECT
            p.id,
            p.name,
            p.price,
            p.stock_qty,
            p.category,
            c.name AS company_name,
            c.website
        FROM r_luxai.products p
        LEFT JOIN r_luxai.companies c ON c.id = p.companies_id
        WHERE
            p.category ILIKE %s
            OR p.name ILIKE %s
            OR p.attributes::text ILIKE %s
        ORDER BY p.price ASC NULLS LAST
        LIMIT 5;
    """

    product_type = position.get('product_type') or ''
    product_name = position.get('product_name') or ''
    search_text = product_name or product_type
    search = f"%{search_text}%"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, [search, search, search])
            rows = cur.fetchall()

    shops = []

    for row in rows:
        shops.append({
            'id': row['id'],
            'name': row['company_name'] or 'Поставщик не указан',
            'price': format_money(row['price']),
            'delivery': (
                f"Остаток: {row['stock_qty']} шт."
                if row['stock_qty'] is not None
                else 'Остаток не указан'
            ),
            'rating': '-',
            'url': row['website'] or 'https://example.com',
        })

    return shops


def fetch_selected_items(application, selected_shops_ids):
    selected_items = []

    for item in application['items']:
        selected_shop_id = selected_shops_ids.get(item['id'])

        if selected_shop_id:
            selected_shop = None

            for shop in item['shops']:
                if shop['id'] == selected_shop_id:
                    selected_shop = shop
                    break

            if selected_shop:
                selected_items.append({
                    'item': item,
                    'shop': selected_shop,
                })

    return selected_items


def normalize_components(components):
    if not components:
        return []

    result = []

    for component in components[:12]:
        if isinstance(component, dict):
            result.append({
                'group': component.get('group') or 'Комплектация',
                'name': component.get('name') or '',
            })
        else:
            result.append({
                'group': 'Комплектация',
                'name': str(component),
            })

    return result


def normalize_key_requirements(requirements):
    if not requirements:
        return []

    labels = {
        'user_type': 'Пользователь',
        'education_level': 'Уровень образования',
        'subject_area': 'Предметная область',

        'software': 'ПО',
        'manual': 'Руководство',
        'storage_system': 'Система хранения',

        'modules_count': 'Модулей',
        'material': 'Материал',
        'touch_panel': 'Сенсорная панель',
        'touch_points_min': 'Касаний от',
        'screen_resolution_min': 'Разрешение от',

        'ram_min_gb': 'RAM от',
        'storage_min_gb': 'Накопитель от',
        'ssd_min_gb': 'SSD от',
        'cpu_min': 'CPU от',
        'cpu_type': 'CPU',
        'cpu_frequency_min_ghz': 'Частота CPU от',
        'hdmi_ports_min': 'HDMI от',

        'equipment_type': 'Тип оборудования',
        'case_material': 'Материал корпуса',
        'projector': 'Проектор',
        'built_in_computer': 'Встроенный ПК',
        'keyboard_mouse': 'Клавиатура и мышь',

        'projection_length_m': 'Длина проекции',
        'projection_height_m': 'Высота проекции',
        'projection_width_m': 'Ширина проекции',

        'camera_resolution_min': 'Камера от',
        'camera_scan_rate_min_fps': 'FPS камеры от',
        'contrast': 'Контрастность',
        'brightness_lm': 'Яркость',

        'interactive_globe': 'Интерактивный глобус',
        'tablet': 'Планшет',
        'interactive_panel': 'Интерактивная панель',
        'quiz_questions_min': 'Вопросов от',
        'multitouch_points_min': 'Мультитач от',
        'tablet_screen_min_inches': 'Экран планшета от',
        'tablet_ram_min_gb': 'RAM планшета от',
        'tablet_storage_min_gb': 'Память планшета от',
        'tablet_battery_min_mah': 'АКБ планшета от',

        'temperature_sensor': 'Датчик температуры',
        'magnetic_field_sensor': 'Датчик магнитного поля',
        'ph_sensor': 'Датчик pH',
        'absolute_pressure_sensor': 'Датчик давления',
        'ultrasonic_distance_sensor': 'Датчик расстояния',
        'conductivity_sensor': 'Датчик электропроводности',
        'sound_sensor': 'Датчик звука',
        'light_sensor': 'Датчик освещенности',
        'oscilloscope_voltage_sensor': 'Датчик напряжения',
        'optoelectronic_sensor': 'Оптоэлектрический датчик',
        'current_sensor': 'Датчик тока',
        'humidity_sensor': 'Датчик влажности',

        'wireless_data_kit': 'Беспроводная передача данных',
        'usb_cables_min': 'USB-кабелей от',
        'software_flash_drive': 'Флеш-накопитель с ПО',
        'methodical_recommendations': 'Методические рекомендации',
        'methodical_manual': 'Методическое руководство',
        'experiment_equipment_set': 'Комплект для опытов',

        'teacher_kit': 'Комплект учителя',
        'primary_school_lab': 'Лаборатория начальной школы',
        'optics_set': 'Набор по оптике',
        'mechanics_set': 'Набор по механике',
        'chemistry_experiments_set': 'Набор по химии',
        'electricity_set': 'Набор по электричеству',
        'soap_bubbles_set': 'Набор мыльных пузырей',
        'container_rack_min': 'Стойка контейнеров от',

        'digital_microscope': 'Цифровой микроскоп',
        'electronic_scales': 'Электронные весы',
        'backpack': 'Рюкзак',

        'wall_mode': 'Режим стены',
        'floor_projection': 'Проекция на пол',
        'projector_type': 'Тип проектора',
        'height_mm': 'Высота',
        'floor_cover_area_m2': 'Площадь покрытия',
        'usb_2_0': 'USB 2.0',

        'sensors': 'Датчики',
        'software_sections': 'Разделы ПО',
        'software_features': 'Функции ПО',
        'wifi_standards': 'Wi-Fi',
    }

    units = {
        'touch_points_min': 'кас.',
        'ram_min_gb': 'ГБ',
        'storage_min_gb': 'ГБ',
        'ssd_min_gb': 'ГБ',
        'tablet_ram_min_gb': 'ГБ',
        'tablet_storage_min_gb': 'ГБ',
        'tablet_battery_min_mah': 'мА·ч',
        'tablet_screen_min_inches': '"',
        'cpu_frequency_min_ghz': 'ГГц',
        'camera_scan_rate_min_fps': 'к/с',
        'brightness_lm': 'лм',
        'hdmi_ports_min': 'шт.',
        'usb_cables_min': 'шт.',
        'quiz_questions_min': 'шт.',
        'multitouch_points_min': 'кас.',
        'container_rack_min': 'конт.',
        'projection_length_m': 'м',
        'projection_height_m': 'м',
        'projection_width_m': 'м',
        'height_mm': 'мм',
        'floor_cover_area_m2': 'м²',
    }

    normalized = []

    for key, value in requirements.items():
        if value is None or value is False:
            continue

        label = labels.get(key, key)
        unit = units.get(key)

        normalized.append({
            'label': label,
            'value': format_requirement_value(value, unit),
        })

    return normalized[:10]


def format_requirement_value(value, unit=None):
    if value is True:
        return 'Да'

    if isinstance(value, list):
        display_value = ', '.join(str(item) for item in value[:6])

        if len(value) > 6:
            display_value += f' и ещё {len(value) - 6}'

        return display_value

    value = str(value).strip()
    value = humanize_range(value)

    if unit:
        return add_unit(value, unit)

    return value


def humanize_range(value):
    clean = value

    for symbol in ['>=', '<=', '>', '<', '≥', '≤']:
        clean = clean.replace(symbol, '')

    clean = clean.replace(' и ', ' - ')
    clean = clean.replace('  ', ' ')
    clean = clean.strip()

    parts = [part.strip() for part in clean.split('-')]

    if len(parts) == 2 and parts[0] and parts[1]:
        return f'{parts[0]}–{parts[1]}'

    return clean


def add_unit(value, unit):
    if not value:
        return value

    if unit == '"':
        return f'{value}"'

    return f'{value} {unit}'


def format_quantity(value):
    if value is None:
        return '-'

    return str(value)


def format_money(value):
    if value is None:
        return '-'

    try:
        value = float(value)
        return f'{value:,.0f} ₽'.replace(',', ' ')
    except (TypeError, ValueError):
        return str(value)


def format_date(value):
    if value is None:
        return '-'

    try:
        return value.strftime('%d.%m.%Y')
    except AttributeError:
        return str(value)