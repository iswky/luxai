# webui/db_repository.py

from .db import get_connection


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
    """
    Детальная заявка:
    tender + tender_positions + products как варианты где купить.
    """

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
            min_ram_gb,
            min_storage_gb,
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
        item = {
            'id': position['id'],
            'name': position['product_type'] or 'Позиция без названия',
            'quantity': position['quantity'] or '-',
            'requirements': build_requirements_text(position),
            'budget': position['max_price'] or '-',
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