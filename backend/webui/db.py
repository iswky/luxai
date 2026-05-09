import psycopg2
from psycopg2.extras import RealDictCursor


DB_CONFIG = {
    'host': 'localhost',
    'port': '5432',
    'dbname': 'appdb',
    'user': 'user',
    'password': 'pass',
}


def get_connection():
    return psycopg2.connect(
        **DB_CONFIG,
        cursor_factory=RealDictCursor,
    )
