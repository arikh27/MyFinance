import os
from secrets import compare_digest

from fuzzy_logic import analyze_finances

from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from pydantic import BaseModel
from datetime import date
from math import isfinite

from database import initialize_database, get_connection


app = FastAPI(
    title="MyFinance",
    description="Aplikasi Monitoring Keuangan Pribadi",
    version="1.0.0"
)

initialize_database()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path

    if path in ["/login", "/logout"] or path.startswith("/static/"):
        return await call_next(request)

    if not request.session.get("authenticated"):
        if path.startswith("/api/"):
            return JSONResponse(
                {"detail": "Silakan login terlebih dahulu"},
                status_code=401
            )

        return RedirectResponse("/login", status_code=303)

    return await call_next(request)


app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET"),
    session_cookie="myfinance_session",
    max_age=60 * 60 * 8,
    same_site="lax",
    https_only=os.getenv("SESSION_HTTPS_ONLY", "false").lower() == "true"
)

# Model data transaksi
class Transaction(BaseModel):
    type: str
    category: str
    amount: float
    description: str = ""
    transaction_date: date


# Model data anggaran
class Budget(BaseModel):
    initial_balance: float
    fixed_expenses: float = 0
    savings_target: float = 0
    start_date: date
    end_date: date
    budget_mode: str = "otomatis"
    manual_daily_budget: float | None = None

# Halaman login
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if request.session.get("authenticated"):
        return RedirectResponse("/", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": None}
    )


# Proses login
@app.post("/login", response_class=HTMLResponse)
def login(request: Request, password: str = Form(...)):
    expected_password = os.getenv("APP_PASSWORD")

    if not expected_password:
        raise HTTPException(
            status_code=500,
            detail="APP_PASSWORD belum dikonfigurasi."
        )

    if not compare_digest(password, expected_password):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Password yang kamu masukkan salah."},
            status_code=401
        )

    request.session["authenticated"] = True

    return RedirectResponse("/", status_code=303)


# Proses logout
@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
# Halaman utama
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )


# Status backend
@app.get("/api/status")
def status():
    return {
        "app": "MyFinance",
        "status": "Berjalan"
    }


# Menambahkan transaksi
@app.post("/api/transactions")
def add_transaction(transaction: Transaction):

    if transaction.type not in ["pemasukan", "pengeluaran"]:
        raise HTTPException(
            status_code=400,
            detail="Jenis transaksi tidak valid"
        )

    if not transaction.category.strip():
        raise HTTPException(
            status_code=400,
            detail="Kategori transaksi wajib diisi"
        )

    if (
        not isfinite(transaction.amount)
        or transaction.amount <= 0
    ):
        raise HTTPException(
            status_code=400,
            detail="Nominal harus berupa angka valid dan lebih dari 0"
        )

    if not isinstance(transaction.transaction_date, date):
        raise HTTPException(
            status_code=400,
            detail="Tanggal transaksi tidak valid"
        )

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO transactions
                (type, category, amount, description, transaction_date)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (
                transaction.type,
                transaction.category.strip(),
                transaction.amount,
                transaction.description,
                transaction.transaction_date.isoformat()
            ))

            transaction_id = cursor.fetchone()["id"]

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    return {
        "message": "Transaksi berhasil disimpan",
        "id": transaction_id
    }


# Melihat seluruh transaksi
@app.get("/api/transactions")
def get_transactions():

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM transactions
                ORDER BY transaction_date DESC, id DESC
            """)

            transactions = cursor.fetchall()

        return transactions

    finally:
        conn.close()


# Ringkasan keuangan
@app.get("/api/summary")
def get_summary():

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            cursor.execute("""
                SELECT * FROM budgets
                ORDER BY id DESC LIMIT 1
            """)

            budget = cursor.fetchone()

            if budget is None:

                cursor.execute("""
                    SELECT
                        COALESCE(SUM(CASE
                            WHEN type = 'pemasukan' THEN amount
                            ELSE 0
                        END), 0) AS total_income,
                        COALESCE(SUM(CASE
                            WHEN type = 'pengeluaran' THEN amount
                            ELSE 0
                        END), 0) AS total_expense
                    FROM transactions
                """)

                result = cursor.fetchone()

                income = result["total_income"]
                expense = result["total_expense"]

                return {
                    "total_pemasukan": income,
                    "total_pengeluaran": expense,
                    "saldo": income - expense
                }

            today = date.today().isoformat()

            cursor.execute("""
                SELECT
                    COALESCE(SUM(CASE
                        WHEN type = 'pemasukan' THEN amount
                        ELSE 0
                    END), 0) AS total_income,
                    COALESCE(SUM(CASE
                        WHEN type = 'pengeluaran' THEN amount
                        ELSE 0
                    END), 0) AS total_expense
                FROM transactions
                WHERE transaction_date BETWEEN %s AND %s
            """, (budget["start_date"], today))

            result = cursor.fetchone()

            income = result["total_income"]
            expense = result["total_expense"]

            balance = (
                budget["initial_balance"]
                + income
                - expense
            )

            return {
                "total_pemasukan": income,
                "total_pengeluaran": expense,
                "saldo": balance
            }

    finally:
        conn.close()


# Mengambil pengaturan anggaran
@app.get("/api/budgets")
def get_budget():

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM budgets
                ORDER BY id DESC LIMIT 1
            """)

            result = cursor.fetchone()

        if result is None:
            return {"message": "Anggaran belum diatur"}

        return result

    finally:
        conn.close()


# Menyimpan pengaturan anggaran
@app.post("/api/budgets")
def save_budget(budget: Budget):

    if (
        not isfinite(budget.initial_balance)
        or budget.initial_balance <= 0
    ):
        raise HTTPException(
            status_code=400,
            detail="Dana periode harus berupa angka valid dan lebih dari 0"
        )

    if (
        not isfinite(budget.fixed_expenses)
        or budget.fixed_expenses < 0
    ):
        raise HTTPException(
            status_code=400,
            detail="Pengeluaran tetap tidak boleh negatif atau tidak valid"
        )

    if (
        not isfinite(budget.savings_target)
        or budget.savings_target < 0
    ):
        raise HTTPException(
            status_code=400,
            detail="Target tabungan tidak boleh negatif atau tidak valid"
        )

    if budget.end_date < budget.start_date:
        raise HTTPException(
            status_code=400,
            detail="Tanggal akhir tidak boleh lebih awal dari tanggal awal"
        )

    total_days = (
        budget.end_date - budget.start_date
    ).days + 1

    if budget.budget_mode not in ["otomatis", "manual"]:
        raise HTTPException(
            status_code=400,
            detail="Mode anggaran tidak valid"
        )

    available_funds = (
        budget.initial_balance
        - budget.fixed_expenses
        - budget.savings_target
    )

    if available_funds <= 0:
        raise HTTPException(
            status_code=400,
            detail="Dana tidak mencukupi setelah pengeluaran tetap dan tabungan"
        )

    if budget.budget_mode == "otomatis":

        daily_budget = available_funds / total_days

    else:

        if (
            budget.manual_daily_budget is None
            or not isfinite(budget.manual_daily_budget)
            or budget.manual_daily_budget <= 0
        ):
            raise HTTPException(
                status_code=400,
                detail="Anggaran manual harus berupa angka valid dan lebih dari 0"
            )

        daily_budget = budget.manual_daily_budget

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO budgets (
                    initial_balance,
                    fixed_expenses,
                    savings_target,
                    daily_budget,
                    start_date,
                    end_date,
                    budget_mode
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                budget.initial_balance,
                budget.fixed_expenses,
                budget.savings_target,
                daily_budget,
                budget.start_date.isoformat(),
                budget.end_date.isoformat(),
                budget.budget_mode
            ))

            budget_id = cursor.fetchone()["id"]

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    return {
        "message": "Anggaran berhasil disimpan",
        "id": budget_id,
        "budget_mode": budget.budget_mode,
        "daily_budget": daily_budget,
        "total_days": total_days
    }


# Analisis keuangan menggunakan Fuzzy Mamdani
@app.get("/api/fuzzy-analysis")
def fuzzy_analysis():

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            cursor.execute("""
                SELECT * FROM budgets
                ORDER BY id DESC LIMIT 1
            """)

            budget = cursor.fetchone()

            if budget is None:
                raise HTTPException(
                    status_code=400,
                    detail="Pengaturan anggaran belum tersedia"
                )

            today = date.today()

            start_date = date.fromisoformat(budget["start_date"])
            end_date = date.fromisoformat(budget["end_date"])

            if today < start_date or today > end_date:
                raise HTTPException(
                    status_code=400,
                    detail="Tanggal hari ini di luar periode anggaran"
                )

            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) AS spending_today
                FROM transactions
                WHERE type = 'pengeluaran'
                AND transaction_date = %s
            """, (today.isoformat(),))

            spending_today = cursor.fetchone()["spending_today"]

            cursor.execute("""
                SELECT
                    COALESCE(SUM(CASE
                        WHEN type = 'pemasukan' THEN amount
                        ELSE 0
                    END), 0) AS income,
                    COALESCE(SUM(CASE
                        WHEN type = 'pengeluaran' THEN amount
                        ELSE 0
                    END), 0) AS expense
                FROM transactions
                WHERE transaction_date BETWEEN %s AND %s
            """, (
                budget["start_date"],
                today.isoformat()
            ))

            result = cursor.fetchone()

            current_balance = (
                budget["initial_balance"]
                + result["income"]
                - result["expense"]
            )

            remaining_days = (end_date - today).days + 1

            if current_balance < 0:
                current_balance = 0

            analysis = analyze_finances(
                spending_today=spending_today,
                daily_budget=budget["daily_budget"],
                current_balance=current_balance,
                remaining_days=remaining_days
            )

            return {
                "tanggal_analisis": today.isoformat(),
                "pengeluaran_hari_ini": spending_today,
                "saldo_saat_ini": current_balance,
                "anggaran_harian": budget["daily_budget"],
                "sisa_hari": remaining_days,
                "analisis_fuzzy": analysis
            }

    finally:
        conn.close()


# Menghapus transaksi berdasarkan ID
@app.delete("/api/transactions/{transaction_id}")
def delete_transaction(transaction_id: int):

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM transactions WHERE id = %s",
                (transaction_id,)
            )

            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=404,
                    detail="Transaksi tidak ditemukan"
                )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    return {
        "message": "Transaksi berhasil dihapus",
        "id": transaction_id
    }
