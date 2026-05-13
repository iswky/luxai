import sys
import csv
import argparse
import psycopg2
from psycopg2 import sql

def main():
    parser = argparse.ArgumentParser(description="Извлечь все строки из lux_ai.companies")
    parser.add_argument("--host", default="localhost", help="Хост PostgreSQL (по умолчанию localhost)")
    parser.add_argument("--port", default="5433", help="Порт PostgreSQL (по умолчанию 5433 для Docker)")
    parser.add_argument("--dbname", default="postgres", help="Имя базы данных")
    parser.add_argument("--user", default="postgres", help="Пользователь")
    parser.add_argument("--password", default="pass", help="Пароль (по умолчанию pass как в примере)")
    parser.add_argument("--output", "-o", help="Сохранить результат в CSV файл (если не указан, вывод в консоль)")

    args = parser.parse_args()

    conn_params = {
        "host": args.host,
        "port": args.port,
        "dbname": args.dbname,
        "user": args.user,
        "password": args.password
    }

    try:
        conn = psycopg2.connect(**conn_params)
        cur = conn.cursor()

        cur.execute("SELECT * FROM lux_ai.companies;")

        colnames = [desc[0] for desc in cur.description]

        rows = cur.fetchall()

        if args.output:
            with open(args.output, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(colnames)
                writer.writerows(rows)
            print(f"✅ Данные сохранены в {args.output}")
        else:
            # print to console (tabular view)
            writer = csv.writer(sys.stdout)
            writer.writerow(colnames)
            writer.writerows(rows)

        cur.close()
        conn.close()

    except psycopg2.Error as e:
        print(f"❌ Ошибка PostgreSQL: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()