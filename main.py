impor os
dari secrets impor compare_digest

dari tanggal dan waktu impor tanggal
dari math impor isfinite

dari fastapi impor FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

dari pydantic impor BaseModel
dari pwdlib impor PasswordHash

dari fuzzy_logic impor analyze_finances
dari database impor initialize_database, dapatkan_koneksi


# =========================================================
# KONFIGURASI APLIKASI
# =========================================================

aplikasi = FastAPI(
    judul="Keuangan Saya",
    deskripsi="Aplikasi Pemantauan Keuangan Pribadi",
    versi="1.0.0"
)

password_hash = PasswordHash.recommended()

# Membuat database tabel jika belum tersedia
initialize_database()

app.mount("/static", StaticFiles(directory="static"), name="static")
template = Jinja2Templates(directory="templates")


# =========================================================
# MIDDLEWARE AUTENTIKASI
# =========================================================

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    jalur = request.url.path

    # Halaman yang boleh dibuka tanpa login
    jalur publik = [
        "/login",
        "/logout",
        "/setup-account"
    ]

    jika path ada di public_paths atau path.startswith("/static/"):
        kembali menunggu panggilan_berikutnya(permintaan)

    # Semua halaman dan API lainnya wajib memiliki sesi pengguna
    jika tidak request.session.get("user_id"):
        jika path.dimulai dengan("/api/"):
            kembalikan JSONResponse(
                {"detail": "Silakan login terlebih dahulu"},
                kode_status=401
            )

        kembalikan RedirectResponse("/login", status_code=303)

    kembali menunggu panggilan_berikutnya(permintaan)


aplikasi.add_middleware(
    SessionMiddleware,
    kunci_rahasia=os.getenv("SEKRET_SESI"),
    session_cookie="myfinance_session",
    usia_maksimum = 60 * 60 * 8,
    situs_sama="longgar",
    https_only=os.getenv("SESSION_HTTPS_ONLY", "false").lower() == "true"
)


# =========================================================
# DATA MODEL
# =========================================================

kelas Transaksi(BaseModel):
    tipe: string
    kategori: str
    jumlah: float
    deskripsi: str = "
    tanggal_transaksi: tanggal


kelas Anggaran(BaseModel):
    saldo_awal: float
    pengeluaran_tetap: float = 0
    target_tabungan: float = 0
    tanggal_mulai: tanggal
    tanggal_akhir: tanggal
    mode_anggaran: str = "otomatis"
    manual_daily_budget: float | None = None


# =========================================================
# SETUP AKUN UTAMA
# =========================================================

EMAIL PEMILIK = "arsannn203@gmail.com"


@app.get("/setup-account", response_class=HTMLResponse)
def setup_account_page(request: Request):
    koneksi = mendapatkan_koneksi()

    mencoba:
        dengan conn.cursor() sebagai kursor:
            kursor.eksekusi("SELECT id FROM users LIMIT 1")
            pengguna_yang_ada = kursor.ambil_satu()
    Akhirnya:
        koneksi.tutup()

    # Setup ditutup jika sudah ada akun
    jika pengguna sudah ada:
        kembalikan RedirectResponse("/login", status_code=303)

    kembalikan template.TemplateResponse(
        permintaan=permintaan,
        nama="setup.html",
        konteks={"kesalahan": Tidak ada}
    )


@app.post("/setup-account", response_class=HTMLResponse)
def setup_account(
    Permintaan: Permintaan,
    nama_lengkap: str = Formulir(...),
    email: str = Formulir(...),
    kata sandi: str = Formulir(...),
    konfirmasi_kata_sandi: str = Formulir(...),
    setup_key: str = Form(...)
):
    expected_key = os.getenv("OWNER_SETUP_KEY")

    jika tidak expected_key:
        menimbulkan HTTPException(
            kode_status=500,
            detail="OWNER_SETUP_KEY belum dikonfigurasi."
        )

    jika tidak membandingkan_digest(setup_key, expected_key):
        menimbulkan HTTPException(
            kode_status=403,
            detail="Kunci pengaturan keamanan tidak valid."
        )

    nama_lengkap = nama_lengkap.strip()
    email = email.strip().lower()

    jika full_name atau len(full_name) tidak lebih dari 100:
        menimbulkan HTTPException(
            kode_status=400,
            detail="Nama lengkap wajib diisi dan maksimal 100 karakter."
        )

    jika email tidak sama dengan EMAIL PEMILIK:
        menimbulkan HTTPException(
            kode_status=400,
            detail="Email akun utama tidak sesuai."
        )

    jika panjang kata sandi kurang dari 12 atau panjang kata sandi lebih dari 128:
        menimbulkan HTTPException(
            kode_status=400,
            detail="Kata sandi harus terdiri dari 12 sampai 128 karakter."
        )

    Jika kata sandi tidak sama dengan konfirmasi kata sandi:
        kembalikan template.TemplateResponse(
            permintaan=permintaan,
            nama="setup.html",
            konteks={"error": "Konfirmasi kata sandi tidak cocok."},
            kode_status=400
        )

    hashed_password = password_hash.hash(password)

    koneksi = mendapatkan_koneksi()

    mencoba:
        dengan conn.cursor() sebagai kursor:
            # Mengunci tabel selama setup agar dua proses setup
            # tidak membuat akun utama secara bersamaan.
            cursor.execute("KUNCI TABEL pengguna DALAM MODE EKSKLUSIF")

            kursor.eksekusi("SELECT id FROM users LIMIT 1")
            pengguna_yang_ada = kursor.ambil_satu()

            jika pengguna sudah ada:
                menimbulkan HTTPException(
                    kode_status=403,
                    detail="Proses setup akun utama sudah ditutup."
                )

            kursor.eksekusi("""
                INSERT INTO users (full_name, email, password_hash)
                NILAI (%s, %s, %s)
                MENGEMBALIKAN id
            "", (
                nama lengkap,
                e-mail,
                kata sandi yang di-hash
            ))

            user_id = cursor.fetchone()["id"]

            # Memindahkan seluruh data lama yang belum dimiliki pemiliknya
            # ke akun utama.
            kursor.eksekusi("""
                PERBARUI transaksi
                SET user_id = %s
                DI MANA user_id BERNILAI NULL
            """, (user_id,))

            kursor.eksekusi("""
                PERBARUI anggaran
                SET user_id = %s
                DI MANA user_id BERNILAI NULL
            """, (user_id,))

        koneksi.commit()

    kecuali Pengecualian:
        koneksi.rollback()
        mengangkat

    Akhirnya:
        koneksi.tutup()

    permintaan.sesi.bersihkan()
    permintaan.session["authenticated"] = True
    permintaan.session["user_id"] = user_id
    permintaan.session["nama_lengkap"] = nama_lengkap

    kembalikan RedirectResponse("/", status_code=303)


# =========================================================
# MASUK DAN KELUAR
# =========================================================

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    jika request.session.get("user_id"):
        kembalikan RedirectResponse("/", status_code=303)

    kembalikan template.TemplateResponse(
        permintaan=permintaan,
        nama="login.html",
        konteks={"kesalahan": Tidak ada}
    )


@app.post("/login", response_class=HTMLResponse)
def login(
    Permintaan: Permintaan,
    email: str = Formulir(...),
    kata sandi: str = Formulir(...)
):
    email = email.strip().lower()

    koneksi = mendapatkan_koneksi()

    mencoba:
        dengan conn.cursor() sebagai kursor:
            kursor.eksekusi("""
                Pilih id, nama_lengkap, hash_kata_sandi
                DARI pengguna
                DI MANA email = %s
            """, (email,))

            pengguna = kursor.ambil()

    Akhirnya:
        koneksi.tutup()

    valid_password = False

    jika pengguna:
        kata_sandi_valid = hash_sandi.verifikasi(
            kata sandi,
            pengguna["hash_kata_sandi"]
        )

    jika kata sandi tidak valid:
        kembalikan template.TemplateResponse(
            permintaan=permintaan,
            nama="login.html",
            konteks={"error": "Email atau kata sandi tidak sesuai."},
            kode_status=401
        )

    permintaan.sesi.bersihkan()
    permintaan.session["authenticated"] = True
    permintaan.session["user_id"] = user["id"]
    permintaan.session["nama_lengkap"] = pengguna["nama_lengkap"]

    kembalikan RedirectResponse("/", status_code=303)


@app.post("/logout")
def logout(request: Request):
    permintaan.sesi.bersihkan()
    kembalikan RedirectResponse("/login", status_code=303)


# =========================================================
#HALAMAN UTAMA DAN STATUS BACKEND
# =========================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    kembalikan template.TemplateResponse(
        permintaan=permintaan,
        nama="index.html",
        konteks={
            "nama_lengkap": permintaan.session.get("nama_lengkap")
        }
    )


@app.get("/api/status")
def status():
    kembali {
        "aplikasi": "Keuangan Saya",
        "status": "Berjalan"
    }


# =========================================================
# TRANSAKSI
# =========================================================

@app.post("/api/transactions")
def add_transaction(
    transaksi: Transaksi,
    Permintaan: Permintaan
):
    user_id = request.session["user_id"]

    jika transaksi.ketik tidak ada di ["pemasukan", "pengeluaran"]:
        menimbulkan HTTPException(
            kode_status=400,
            detail="Jenis transaksi tidak valid"
        )

    jika transaction.category.strip() tidak berhasil:
        menimbulkan HTTPException(
            kode_status=400,
            detail="Kategori transaksi wajib diisi"
        )

    jika jumlah transaksi tidak terbatas atau jumlah transaksi kurang dari atau sama dengan 0:
        menimbulkan HTTPException(
            kode_status=400,
            detail="Nominal harus berupa angka valid dan lebih dari 0"
        )

    koneksi = mendapatkan_koneksi()

    mencoba:
        dengan conn.cursor() sebagai kursor:
            kursor.eksekusi("""
                MASUKKAN KE transaksi (
                    ID pengguna,
                    jenis,
                    kategori,
                    jumlah,
                    keterangan,
                    tanggal_transaksi
                )
                NILAI (%s, %s, %s, %s, %s, %s)
                MENGEMBALIKAN id
            "", (
                ID pengguna,
                jenis transaksi,
                transaksi.kategori.strip(),
                jumlah transaksi,
                deskripsi transaksi,
                transaksi.tanggal_transaksi.isoformat()
            ))

            transaction_id = cursor.fetchone()["id"]

        koneksi.commit()

    kecuali Pengecualian:
        koneksi.rollback()
        mengangkat

    Akhirnya:
        koneksi.tutup()

    kembali {
        "message": "Transaksi berhasil disimpan",
        "id": transaction_id
    }


@app.get("/api/transactions")
def get_transactions(request: Request):
    user_id = request.session["user_id"]

    koneksi = mendapatkan_koneksi()

    mencoba:
        dengan conn.cursor() sebagai kursor:
            kursor.eksekusi("""
                PILIH *
                DARI transaksi
                DI MANA user_id = %s
                Urutkan berdasarkan transaction_date DESC, id DESC
            """, (user_id,))

            transaksi = kursor.ambil semua()

        transaksi pengembalian

    Akhirnya:
        koneksi.tutup()


# =========================================================
# RINGKASAN KEUANGAN
# =========================================================

@app.get("/api/summary")
def get_summary(request: Request):
    user_id = request.session["user_id"]

    koneksi = mendapatkan_koneksi()

    mencoba:
        dengan conn.cursor() sebagai kursor:

            # Mengambil anggaran milik pengguna
            kursor.eksekusi("""
                PILIH *
                DARI anggaran
                DI MANA user_id = %s
                Urutkan berdasarkan id menurun
                BATAS 1
            """, (user_id,))

            anggaran = kursor.ambil_satu()

            # Jika pengguna belum memiliki anggaran
            Jika anggaran tidak ada:
                kursor.eksekusi("""
                    MEMILIH
                        COALESCE(SUM(CASE
                            KETIKA ketik = 'pemasukan' MAKA jumlah
                            LAINNYA 0
                        SELESAI), 0) SEBAGAI total_pendapatan,
                        COALESCE(SUM(CASE
                            KETIKA tipe = 'pengeluaran' MAKA jumlah
                            LAINNYA 0
                        AKHIR), 0) SEBAGAI total_pengeluaran
                    DARI transaksi
                    DI MANA user_id = %s
                """, (user_id,))

                hasil = kursor.ambil_yang_di_kantongi()

                pendapatan = hasil["total_pendapatan"]
                pengeluaran = hasil["total_pengeluaran"]

                kembali {
                    "total_pemasukan": pendapatan,
                    "total_pengeluaran": pengeluaran,
                    "saldo": pendapatan - pengeluaran
                }

            # Menghitung transaksi dalam periode anggaran
            hari ini = tanggal.hari ini().isoformat()

            kursor.eksekusi("""
                MEMILIH
                    COALESCE(SUM(CASE
                        KETIKA ketik = 'pemasukan' MAKA jumlah
                        LAINNYA 0
                    SELESAI), 0) SEBAGAI total_pendapatan,
                    COALESCE(SUM(CASE
                        KETIKA tipe = 'pengeluaran' MAKA jumlah
                        LAINNYA 0
                    AKHIR), 0) SEBAGAI total_pengeluaran
                DARI transaksi
                DI MANA user_id = %s
                DAN transaction_date ANTARA %s DAN %s
            "", (
                ID pengguna,
                anggaran["tanggal_mulai"],
                Hari ini
            ))

            hasil = kursor.ambil_yang_di_kantongi()

            pendapatan = hasil["total_pendapatan"]
            pengeluaran = hasil["total_pengeluaran"]

            saldo = (
                anggaran["saldo_awal"]
                + pendapatan
                - pengeluaran
            )

            kembali {
                "total_pemasukan": pendapatan,
                "total_pengeluaran": pengeluaran,
                "saldo": keseimbangan
            }

    Akhirnya:
        koneksi.tutup()


# =========================================================
# PENGATURAN ANGGARAN
# =========================================================

@app.get("/api/budgets")
def get_budget(request: Request):
    user_id = request.session["user_id"]

    koneksi = mendapatkan_koneksi()

    mencoba:
        dengan conn.cursor() sebagai kursor:
            kursor.eksekusi("""
                PILIH *
                DARI anggaran
                DI MANA user_id = %s
                Urutkan berdasarkan id menurun
                BATAS 1
            """, (user_id,))

            hasil = kursor.ambil_yang_di_kantongi()

        jika hasilnya None:
            return {"message": "Anggaran belum diatur"}

        kembalikan hasil

    Akhirnya:
        koneksi.tutup()


@app.post("/api/budgets")
def save_budget(
    Anggaran: Anggaran,
    Permintaan: Permintaan
):
    user_id = request.session["user_id"]

    jika tidak tak terbatas (saldo awal anggaran) atau saldo awal anggaran <= 0:
        menimbulkan HTTPException(
            kode_status=400,
            detail="Dana periode harus berupa angka valid dan lebih dari 0"
        )

    jika anggaran tetap tidak terbatas atau anggaran tetap kurang dari 0:
        menimbulkan HTTPException(
            kode_status=400,
            detail="Pengeluaran tetap tidak boleh negatif atau tidak valid"
        )

    jika tidak tak terbatas (anggaran.target_penghematan) atau anggaran.target_penghematan < 0:
        menimbulkan HTTPException(
            kode_status=400,
            detail="Target tabungan tidak boleh negatif atau tidak valid"
        )

    jika tanggal_akhir_anggaran < tanggal_mulai_anggaran:
        menimbulkan HTTPException(
            kode_status=400,
            detail="Tanggal akhir tidak boleh lebih awal dari tanggal awal"
        )

    jumlah_hari = (
        tanggal_akhir_anggaran - tanggal_mulai_anggaran
    ).hari + 1

    jika budget.budget_mode tidak ada di ["otomatis", "manual"]:
        menimbulkan HTTPException(
            kode_status=400,
            detail="Mode anggaran tidak valid"
        )

    dana_tersedia = (
        anggaran.saldo_awal
        - anggaran.pengeluaran_tetap
        - target_tabungan_anggaran
    )

    jika dana_tersedia <= 0:
        menimbulkan HTTPException(
            kode_status=400,
            detail="Dana tidak mencukupi setelah pengeluaran tetap dan tabungan"
        )

    if budget.budget_mode == "otomatis":
        Anggaran harian = dana yang tersedia / total hari

    kalau tidak:
        jika (
            budget.manual_daily_budget adalah None
            atau tidak terbatas (anggaran.anggaran_harian_manual)
            atau budget.manual_daily_budget <= 0
        ):
            menimbulkan HTTPException(
                kode_status=400,
                detail="Anggaran manual harus berupa angka valid dan lebih dari 0"
            )

        anggaran_harian = anggaran.anggaran_harian_manual

    koneksi = mendapatkan_koneksi()

    mencoba:
        dengan conn.cursor() sebagai kursor:
            kursor.eksekusi("""
                MASUKKAN KE dalam anggaran (
                    ID pengguna,
                    saldo_awal,
                    pengeluaran tetap,
                    target_tabungan,
                    anggaran harian,
                    tanggal_mulai,
                    tanggal_akhir,
                    mode_anggaran
                )
                NILAI (%s, %s, %s, %s, %s, %s, %s, %s)
                MENGEMBALIKAN id
            "", (
                ID pengguna,
                anggaran.saldo_awal,
                anggaran.pengeluaran_tetap,
                target_tabungan_anggaran,
                anggaran harian,
                anggaran.tanggal_mulai.isoformat(),
                budget.end_date.isoformat(),
                anggaran.mode_anggaran
            ))

            budget_id = cursor.fetchone()["id"]

        koneksi.commit()

    kecuali Pengecualian:
        koneksi.rollback()
        mengangkat

    Akhirnya:
        koneksi.tutup()

    kembali {
        "message": "Anggaran berhasil disimpan",
        "id": id_anggaran,
        "mode_anggaran": anggaran.mode_anggaran,
        "anggaran_harian": anggaran_harian,
        "jumlah_hari": jumlah_hari
    }


# =========================================================
#ANALISIS KEUANGAN FUZZY MAMDANI
# =========================================================

@app.get("/api/fuzzy-analysis")
def fuzzy_analysis(request: Request):
    user_id = request.session["user_id"]

    koneksi = mendapatkan_koneksi()

    mencoba:
        dengan conn.cursor() sebagai kursor:

            # Mengambil anggaran milik pengguna
            kursor.eksekusi("""
                PILIH *
                DARI anggaran
                DI MANA user_id = %s
                Urutkan berdasarkan id menurun
                BATAS 1
            """, (user_id,))

            anggaran = kursor.ambil_satu()

            Jika anggaran tidak ada:
                menimbulkan HTTPException(
                    kode_status=400,
                    detail="Pengaturan anggaran belum tersedia"
                )

            hari ini = tanggal.hari ini()

            tanggal_mulai = tanggal.fromisoformat(anggaran["tanggal_mulai"])
            tanggal_akhir = tanggal.fromisoformat(anggaran["tanggal_akhir"])

            jika hari ini < start_date atau hari ini > end_date:
                menimbulkan HTTPException(
                    kode_status=400,
                    detail="Tanggal hari ini di luar periode anggaran"
                )

            # Menghitung pengeluaran hari ini milik pengguna
            kursor.eksekusi("""
                SELECT COALESCE(SUM(amount), 0) AS spending_today
                DARI transaksi
                DI MANA user_id = %s
                DAN tipe = 'pengeluaran'
                DAN transaction_date = %s
            "", (
                ID pengguna,
                hari ini.isoformat()
            ))

            pengeluaran_hari_ini = kursor.ambil_satu()["pengeluaran_hari_ini"]

            # Menghitung pemasukan dan periode pengeluaran
            kursor.eksekusi("""
                MEMILIH
                    COALESCE(SUM(CASE
                        KETIKA ketik = 'pemasukan' MAKA jumlah
                        LAINNYA 0
                    SELESAI), 0) SEBAGAI pendapatan,
                    COALESCE(SUM(CASE
                        KETIKA tipe = 'pengeluaran' MAKA jumlah
                        LAINNYA 0
                    SELESAI), 0) SEBAGAI pengeluaran
                DARI transaksi
                DI MANA user_id = %s
                DAN transaction_date ANTARA %s DAN %s
            "", (
                ID pengguna,
                anggaran["tanggal_mulai"],
                hari ini.isoformat()
            ))

            hasil = kursor.ambil_yang_di_kantongi()

            saldo_saat_ini = (
                anggaran["saldo_awal"]
                + hasil["pendapatan"]
                - hasil["pengeluaran"]
            )

            sisa_hari = (tanggal_akhir - hari_ini).hari + 1

            jika saldo saat ini < 0:
                saldo_saat_ini = 0

            # Garis analisis Fuzzy Mamdani
            analisis = menganalisis_keuangan(
                pengeluaran_hari_ini=pengeluaran_hari_ini,
                anggaran_harian=anggaran["anggaran_harian"],
                saldo_saat_ini=saldo_saat_ini,
                hari_tersisa=hari_tersisa
            )

            kembali {
                "tanggal_analisis": hari ini.isoformat(),
                "pengeluaran_hari_ini": pembelanjaan_hari ini,
                "saldo_saat_ini": saldo_saat ini,
                "anggaran_harian": anggaran["anggaran_harian"],
                "sisa_hari": hari_tersisa,
                "analisis_fuzzy": analisis
            }

    Akhirnya:
        koneksi.tutup()


# =========================================================
# MENGHAPUS TRANSAKSI
# =========================================================

@app.delete("/api/transactions/{transaction_id}")
def delete_transaction(
    ID transaksi: int,
    Permintaan: Permintaan
):
    user_id = request.session["user_id"]

    koneksi = mendapatkan_koneksi()

    mencoba:
        dengan conn.cursor() sebagai kursor:
            kursor.eksekusi("""
                HAPUS DARI transaksi
                DI MANA id = %s
                DAN user_id = %s
            "", (
                ID transaksi,
                ID pengguna
            ))

            jika cursor.rowcount == 0:
                menimbulkan HTTPException(
                    kode_status=404,
                    detail="Transaksi tidak ditemukan"
                )

        koneksi.commit()

    kecuali Pengecualian:
        koneksi.rollback()
        mengangkat

    Akhirnya:
        koneksi.tutup()

    kembali {
        "message": "Transaksi berhasil dihapus",
        "id": transaction_id
}
