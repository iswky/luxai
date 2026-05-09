# webui/db.py

import psycopg2
from psycopg2.extras import RealDictCursor


DB_CONFIG = {
    # Если Django запускаешь локально через python manage.py runserver:
    'host': 'localhost',
    'port': '5432',

    # Значения из docker-compose.yml
    'dbname': 'appdb',
    'user': 'user',
    'password': 'pass',
}


def get_connection():
    return psycopg2.connect(
        **DB_CONFIG,
        cursor_factory=RealDictCursor,
    )
