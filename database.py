
import os
import psycopg
from psycopg.rows import dict_row


def get_connection():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL belum tersedia.")

    return psycopg.connect(
        database_url,
        row_factory=dict_row
    )


def create_tables():
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id BIGSERIAL PRIMARY KEY,
                    type TEXT NOT NULL,
                    category TEXT NOT NULL,
                    amount DOUBLE PRECISION NOT NULL,
                    description TEXT,
                    transaction_date TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS budgets (
                    id BIGSERIAL PRIMARY KEY,
                    initial_balance DOUBLE PRECISION NOT NULL,
                    fixed_expenses DOUBLE PRECISION DEFAULT 0,
                    savings_target DOUBLE PRECISION DEFAULT 0,
                    daily_budget DOUBLE PRECISION NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    budget_mode TEXT DEFAULT 'otomatis'
                )
            """)

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def initialize_database():
    create_tables()
