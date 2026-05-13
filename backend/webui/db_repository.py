# webui/db_repository.py

from .db import get_connection


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


def format_requirement_value(key, value, unit=None):
    if value is True:
        return 'Да'

    if isinstance(value, list):
        display_value = ', '.join(str(item) for item in value[:6])

        if len(value) > 6:
            display_value += f' и ещё {len(value) - 6}'

        return display_value

    value = str(value).strip()

    range_value = humanize_range(value)

    if unit:
        return add_unit(range_value, unit)

    return range_value


def humanize_range(value):
    replacements = {
        '>=': '',
        '<=': '',
        '>': '',
        '<': '',
        '≥': '',
        '≤': '',
    }

    clean = value

    for old, new in replacements.items():
        clean = clean.replace(old, new)

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

        'sensors': 'Датчики',
        'software_sections': 'Разделы ПО',
        'software_features': 'Функции ПО',
        'wifi_standards': 'Wi-Fi',

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

        display_value = format_requirement_value(key, value, unit)

        normalized.append({
            'label': label,
            'value': display_value,
        })

    return normalized[:8]


def fetch_files():
    """
    Пока отдельной таблицы файлов нет, поэтому собираем файлы из tenders.
    Потом лучше сделать таблицу tender_documents.
    """

    query = """
        SELECT
            id,
            tender_number,
            customer_name,
            status
        FROM r_luxai.tenders
        ORDER BY createdate DESC;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

    files = []

    for row in rows:
        files.append({
            'id': row['id'],
            'name': f"{row['tender_number']}.pdf",
            'source': 'Госзакупки',
            'status': row['status'] or 'Новая',
            'confidence': '-',
            'comment': row['customer_name'] or '',
            'parse_prompt': 'Извлечь товары, количество, характеристики, сроки и требования.',
            'application_file': '/static/webui/files/application_form.pdf',
        })

    return files


def fetch_equipment():
    """
    Данные для страницы сравнения.
    Берём товары из products и подтягиваем компанию.
    """

    query = """
        SELECT
            p.id,
            p.name AS item,
            p.category,
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


def fetch_applications():
    """
    Список тендеров для страницы /applications/.
    Без товаров внутри, только карточки.
    """

    query = """
        SELECT
            id,
            tender_number,
            customer_name,
            closing_date,
            total_budget,
            status
        FROM r_luxai.tenders
        ORDER BY createdate DESC;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

    applications = []

    for row in rows:
        applications.append({
            'id': row['id'],
            'title': f"Тендер {row['tender_number']}",
            'number': row['tender_number'],
            'customer': row['customer_name'] or 'Не указан',
            'deadline': row['closing_date'] or '-',
            'price': row['total_budget'] or '-',
            'status': row['status'] or 'Новая',
            'file': '/static/webui/files/application_form.pdf',
            'items': [],
        })

    return applications


def fetch_application_detail(application_id):
    tender_query = """
        SELECT
            id,
            tender_number,
            customer_name,
            closing_date,
            total_budget,
            status
        FROM r_luxai.tenders
        WHERE id = %s;
    """

    positions_query = """
        SELECT
            id,
            product_type,
            quantity,
            max_price,
            min_cpu,
            min_cpu_cores,
            min_ram_gb,
            ram_type,
            min_storage_gb,
            storage_type,
            os,
            attributes
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
        'deadline': tender['closing_date'] or '-',
        'price': tender['total_budget'] or '-',
        'status': tender['status'] or 'Новая',
        'file': '/static/webui/files/application_form.pdf',
        'items': [],
    }

    for position in positions:
        attrs = position.get('attributes') or {}
        key_requirements = attrs.get('key_requirements') or {}

        full_name = (
            attrs.get('name')
            or position.get('product_type')
            or 'Позиция без названия'
        )

        category = attrs.get('category') or 'Без категории'

        requirements_summary = (
            attrs.get('requirements_summary')
            or build_requirements_text(position)
        )

        item = {
            'id': position['id'],
            'position_number': attrs.get('position_number') or position['id'],
            'name': full_name,
            'product_type': position.get('product_type') or full_name,
            'category': category,
        'quantity': format_quantity(position.get('quantity')),
        'unit': attrs.get('unit') or 'шт',
            'requirements': requirements_summary,
            'key_requirements': normalize_key_requirements(key_requirements),
            'budget': format_money(position.get('max_price')),
            'shops': fetch_shops_for_position(position),
        }

        application['items'].append(item)

    return application


def build_requirements_text(position):
    parts = []

    if position.get('min_cpu'):
        parts.append(f"CPU: {position['min_cpu']}")

    if position.get('min_ram_gb'):
        parts.append(f"RAM от {position['min_ram_gb']} GB")

    if position.get('min_storage_gb'):
        parts.append(f"Накопитель от {position['min_storage_gb']} GB")

    if position.get('os'):
        parts.append(f"OS: {position['os']}")

    if position.get('attributes'):
        parts.append(f"Доп. требования: {position['attributes']}")

    if not parts:
        return 'Требования не указаны'

    return ', '.join(parts)


def fetch_shops_for_position(position):
    """
    Временный подбор товаров из products.
    Это ещё не умный поиск, но уже данные из БД.
    """

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
        ORDER BY p.price ASC NULLS LAST
        LIMIT 5;
    """

    product_type = position.get('product_type') or ''
    search = f"%{product_type}%"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, [search, search])
            rows = cur.fetchall()

    shops = []

    for row in rows:
        shops.append({
            'id': row['id'],
            'name': row['company_name'] or 'Поставщик не указан',
            'price': row['price'] or 'Цена не указана',
            'delivery': f"Остаток: {row['stock_qty']}" if row['stock_qty'] is not None else 'Остаток не указан',
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