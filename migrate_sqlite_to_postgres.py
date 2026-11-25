
import os
import sqlite3
import psycopg

from pathlib import Path
from psycopg.rows import dict_row


# Lokasi database SQLite lama
BASE_DIR = Path(__file__).resolve().parent
SQLITE_PATH = BASE_DIR / "myfinance.db"

# Koneksi PostgreSQL Neon
DATABASE_URL = os.getenv("DATABASE_URL")


def migrate_data():

    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL belum tersedia.")

    if not SQLITE_PATH.exists():
        raise FileNotFoundError("File myfinance.db tidak ditemukan.")

    # Membuka database SQLite lama
    sqlite_conn = sqlite3.connect(str(SQLITE_PATH))
    sqlite_conn.row_factory = sqlite3.Row

    # Membuka database PostgreSQL Neon
    pg_conn = psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row
    )

    try:
        sqlite_cursor = sqlite_conn.cursor()

        with pg_conn.cursor() as pg_cursor:

            # Memastikan database Neon belum berisi data
            pg_cursor.execute("""
                SELECT
                    (SELECT COUNT(*) FROM transactions) AS transaction_count,
                    (SELECT COUNT(*) FROM budgets) AS budget_count
            """)

            counts = pg_cursor.fetchone()

            if (
                counts["transaction_count"] > 0
                or counts["budget_count"] > 0
            ):
                raise RuntimeError(
                    "Database Neon sudah berisi data. "
                    "Migrasi dihentikan untuk mencegah duplikasi."
                )

            # Mengambil seluruh transaksi SQLite
            sqlite_cursor.execute("""
                SELECT * FROM transactions ORDER BY id
            """)

            transactions = sqlite_cursor.fetchall()

            for row in transactions:
                pg_cursor.execute("""
                    INSERT INTO transactions (
                        id,
                        type,
                        category,
                        amount,
                        description,
                        transaction_date
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    row["id"],
                    row["type"],
                    row["category"],
                    row["amount"],
                    row["description"],
                    row["transaction_date"]
                ))

            # Mengambil seluruh anggaran SQLite
            sqlite_cursor.execute("""
                SELECT * FROM budgets ORDER BY id
            """)

            budgets = sqlite_cursor.fetchall()

            for row in budgets:
                budget_mode = (
                    row["budget_mode"]
                    if "budget_mode" in row.keys()
                    else "otomatis"
                )

                pg_cursor.execute("""
                    INSERT INTO budgets (
                        id,
                        initial_balance,
                        fixed_expenses,
                        savings_target,
                        daily_budget,
                        start_date,
                        end_date,
                        budget_mode
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    row["id"],
                    row["initial_balance"],
                    row["fixed_expenses"],
                    row["savings_target"],
                    row["daily_budget"],
                    row["start_date"],
                    row["end_date"],
                    budget_mode
                ))

            # Menyesuaikan nomor ID otomatis PostgreSQL
            pg_cursor.execute("""
                SELECT setval(
                    pg_get_serial_sequence('transactions', 'id'),
                    COALESCE(MAX(id), 1),
                    MAX(id) IS NOT NULL
                )
                FROM transactions
            """)

            pg_cursor.execute("""
                SELECT setval(
                    pg_get_serial_sequence('budgets', 'id'),
                    COALESCE(MAX(id), 1),
                    MAX(id) IS NOT NULL
                )
                FROM budgets
            """)

        # Menyimpan hasil migrasi
        pg_conn.commit()

        print("Migrasi berhasil!")
        print("Jumlah transaksi:", len(transactions))
        print("Jumlah anggaran:", len(budgets))

    except Exception:
        pg_conn.rollback()
        raise

    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    migrate_data()
