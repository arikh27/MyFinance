
/* =========================================
   MYFINANCE - REAL TIME FINANCIAL SYSTEM
========================================= */

const menuToggle = document.getElementById("menu-toggle");
const navigationMenu = document.getElementById("navigation-menu");
const navItems = document.querySelectorAll(".nav-item[data-view]");

const rupiah = (angka) => {
    return new Intl.NumberFormat("id-ID", {
        style: "currency",
        currency: "IDR",
        maximumFractionDigits: 0
    }).format(Number(angka) || 0);
};
// Mengubah angka menjadi format ribuan Indonesia
function formatAngkaIndonesia(value) {
    const angka = String(value).replace(/\D/g, "");

    if (!angka) return "";

    return Number(angka).toLocaleString("id-ID");
}

// Memasang format otomatis pada semua input Rupiah
function setupMoneyInputs() {
    const moneyInputs = document.querySelectorAll(".money-input");

    moneyInputs.forEach((input) => {
        input.addEventListener("input", () => {
            const posisiAwal = input.selectionStart;
            const panjangAwal = input.value.length;

            input.value = formatAngkaIndonesia(input.value);

            const selisih = input.value.length - panjangAwal;
            const posisiBaru = Math.max(0, posisiAwal + selisih);

            input.setSelectionRange(posisiBaru, posisiBaru);
        });
    });
}

// Mengambil angka murni untuk dikirim ke backend
function ambilNominal(id) {
    const nilai = document.getElementById(id).value;
    return Number(nilai.replace(/\D/g, "")) || 0;
}
async function fetchJSON(url, options = {}) {
    const response = await fetch(url, options);

    if (response.status === 401) {
        window.location.href = "/login";
        throw new Error("Sesi login telah berakhir.");
    }

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.detail || "Terjadi kesalahan.");
    }

    return data;
}

/* =========================================
   NAVIGASI MENU
========================================= */

function showView(viewName) {
    document.querySelectorAll(".view-section").forEach(section => {
        section.classList.remove("active");
    });

    const selectedView = document.getElementById(`view-${viewName}`);

    if (!selectedView) return;

    selectedView.classList.add("active");

    navItems.forEach(item => {
        item.classList.toggle(
            "active",
            item.dataset.view === viewName
        );
    });

    navigationMenu.classList.add("hidden");
    menuToggle.setAttribute("aria-expanded", "false");

    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });

    if (viewName === "dashboard") {
        refreshDashboard();
    }

    if (viewName === "anggaran") {
        loadBudget();
    }

    if (viewName === "riwayat") {
        loadTransactions();
    }
}

menuToggle.addEventListener("click", () => {
    const isHidden = navigationMenu.classList.toggle("hidden");

    menuToggle.setAttribute(
        "aria-expanded",
        String(!isHidden)
    );
});

navItems.forEach(item => {
    item.addEventListener("click", () => {
        showView(item.dataset.view);
    });
});

document.addEventListener("click", event => {
    if (
        !event.target.closest(".menu-container") &&
        !navigationMenu.classList.contains("hidden")
    ) {
        navigationMenu.classList.add("hidden");
        menuToggle.setAttribute("aria-expanded", "false");
    }
});

document.addEventListener("keydown", event => {
    if (event.key === "Escape") {
        navigationMenu.classList.add("hidden");
        menuToggle.setAttribute("aria-expanded", "false");
    }
});

/* =========================================
   DASHBOARD
========================================= */

async function loadSummary() {
    try {
        const data = await fetchJSON("/api/summary");

        document.getElementById("saldo").textContent =
            rupiah(data.saldo);

        document.getElementById("pemasukan").textContent =
            rupiah(data.total_pemasukan);

        document.getElementById("pengeluaran").textContent =
            rupiah(data.total_pengeluaran);

    } catch (error) {
        console.error("Gagal memuat ringkasan:", error);
    }
}

async function refreshDashboard() {
    await loadSummary();
    await runFuzzyAnalysis();
}

/* =========================================
   RIWAYAT TRANSAKSI
========================================= */

async function loadTransactions() {
    const transactionList = document.getElementById("transaction-list");

    try {
        const transactions = await fetchJSON("/api/transactions");

        transactionList.innerHTML = "";

        if (!transactions || transactions.length === 0) {
            transactionList.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align:center;">
                        Belum ada transaksi.
                    </td>
                </tr>
            `;
            return;
        }

        transactions.forEach(transaction => {
            const row = document.createElement("tr");

            const values = [
                transaction.transaction_date || "-",
                transaction.category || "-",
                transaction.description || "-",
                transaction.type || "-",
                rupiah(transaction.amount)
            ];

            values.forEach(value => {
                const cell = document.createElement("td");
                cell.textContent = value;
                row.appendChild(cell);
            });

            const actionCell = document.createElement("td");

            const deleteButton = document.createElement("button");
            deleteButton.textContent = "Hapus";
            deleteButton.className = "delete-btn";

            deleteButton.addEventListener("click", () => {
                deleteTransaction(transaction.id);
            });

            actionCell.appendChild(deleteButton);
            row.appendChild(actionCell);

            transactionList.appendChild(row);
        });

    } catch (error) {
        console.error("Gagal memuat transaksi:", error);

        transactionList.innerHTML = `
            <tr>
                <td colspan="6">Gagal memuat transaksi.</td>
            </tr>
        `;
    }
}

/* =========================================
   SINKRONISASI SELURUH DATA
========================================= */

async function refreshAllFinancialData() {
    await Promise.all([
        loadSummary(),
        loadTransactions()
    ]);

    await runFuzzyAnalysis();
}

/* =========================================
   TAMBAH TRANSAKSI
========================================= */

const transactionForm = document.getElementById("transaction-form");

const categorySelect = document.getElementById("category");
const otherCategoryField = document.getElementById("other-category-field");
const otherCategoryInput = document.getElementById("other-category");

// Menampilkan kolom kategori tambahan
categorySelect.addEventListener("change", () => {
    if (categorySelect.value === "lainnya") {
        otherCategoryField.classList.remove("hidden");
        otherCategoryInput.required = true;
    } else {
        otherCategoryField.classList.add("hidden");
        otherCategoryInput.required = false;
        otherCategoryInput.value = "";
    }
});

transactionForm.addEventListener("submit", async event => {
    event.preventDefault();

    const message = document.getElementById("form-message");

    
const selectedCategory = categorySelect.value;

const finalCategory = selectedCategory === "lainnya"
    ? otherCategoryInput.value.trim()
    : selectedCategory;

const transaction = {
    type: document.getElementById("type").value,
    category: finalCategory,
    amount: ambilNominal("amount"),
    description: document.getElementById("description").value.trim(),
    transaction_date: document.getElementById("transaction-date").value
};


    try {
        await fetchJSON("/api/transactions", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(transaction)
        });

        message.textContent = "Transaksi berhasil disimpan!";
        message.style.color = "#4de0a5";

        transactionForm.reset();
        setToday();

        await refreshAllFinancialData();

    } catch (error) {
        message.textContent = error.message;
        message.style.color = "#ff647c";
    }
});

/* =========================================
   HAPUS TRANSAKSI
========================================= */

async function deleteTransaction(id) {
    if (!confirm("Yakin ingin menghapus transaksi ini?")) {
        return;
    }

    try {
        await fetchJSON(`/api/transactions/${id}`, {
            method: "DELETE"
        });

        alert("Transaksi berhasil dihapus!");

        await refreshAllFinancialData();

    } catch (error) {
        alert(error.message);
    }
}

/* =========================================
   TANGGAL OTOMATIS
========================================= */

function setToday() {
    const dateInput = document.getElementById("transaction-date");

    if (dateInput) {
        dateInput.value = new Date().toLocaleDateString("en-CA");
    }
}

/* =========================================
   PENGATURAN ANGGARAN
========================================= */

const budgetMode = document.getElementById("budget-mode");
const manualBudgetField = document.getElementById("manual-budget-field");

budgetMode.addEventListener("change", () => {
    if (budgetMode.value === "manual") {
        manualBudgetField.classList.remove("hidden");
    } else {
        manualBudgetField.classList.add("hidden");
    }
});

async function loadBudget() {
    try {
        const data = await fetchJSON("/api/budgets");

        document.getElementById("budget-initial").textContent =
            data.initial_balance !== undefined
                ? rupiah(data.initial_balance)
                : "Belum diatur";

        document.getElementById("daily-budget").textContent =
            data.daily_budget !== undefined
                ? rupiah(data.daily_budget)
                : "Belum diatur";

        document.getElementById("budget-mode-result").textContent =
            data.budget_mode || "Belum diatur";

    } catch (error) {
        console.error("Gagal memuat anggaran:", error);
    }
}

/* =========================================
   SIMPAN ANGGARAN
========================================= */

const budgetForm = document.getElementById("budget-form");

budgetForm.addEventListener("submit", async event => {
    event.preventDefault();

    const message = document.getElementById("budget-message");

    const budget = {
        initial_balance: ambilNominal("initial-balance"),
fixed_expenses: ambilNominal("fixed-expenses"),
savings_target: ambilNominal("savings-target"),
manual_daily_budget: document.getElementById("manual-daily-budget").value.trim()
    ? ambilNominal("manual-daily-budget")
    : null
    };

    try {
        await fetchJSON("/api/budgets", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(budget)
        });

        message.textContent = "Pengaturan anggaran berhasil disimpan!";
        message.style.color = "#4de0a5";

        budgetForm.reset();
        manualBudgetField.classList.add("hidden");

        await loadBudget();
        await refreshAllFinancialData();

    } catch (error) {
        message.textContent = error.message;
        message.style.color = "#ff647c";
    }
});

/* =========================================
   ANALISIS FUZZY MAMDANI
========================================= */

async function runFuzzyAnalysis() {
    const fuzzyMessage = document.getElementById("fuzzy-message");

    try {
        const data = await fetchJSON("/api/fuzzy-analysis");

        const analysis = data.analisis_fuzzy;

        if (!analysis) {
            throw new Error("Hasil analisis belum tersedia.");
        }

        const score = analysis.nilai_fuzzy;
        const status = analysis.status;

        // Update bagian analisis pada halaman anggaran
        document.getElementById("fuzzy-score").textContent = score;
        document.getElementById("fuzzy-status").textContent = status;
        document.getElementById("spending-ratio").textContent =
            analysis.rasio_pengeluaran;
        document.getElementById("balance-ratio").textContent =
            analysis.rasio_kecukupan_saldo;
        document.getElementById("remaining-days").textContent =
            data.sisa_hari;

        fuzzyMessage.textContent =
            "Analisis keuangan berhasil diperbarui.";
        fuzzyMessage.style.color = "#4de0a5";

        // Update kartu status di Dashboard
        document.getElementById("dashboard-fuzzy-score").textContent =
            score;

        document.getElementById("dashboard-fuzzy-status").textContent =
            status;

        document.getElementById("health-indicator").dataset.status =
            String(status).toLowerCase();

        const title = document.getElementById("dashboard-health-title");
        const description = document.getElementById(
            "dashboard-health-description"
        );

        if (status.toLowerCase() === "aman") {
            title.textContent = "Keuangan dalam kondisi aman";
            description.textContent =
                "Kondisi keuangan masih terkendali. Pertahankan kebiasaan mengatur pengeluaran.";
        } else if (status.toLowerCase() === "waspada") {
            title.textContent = "Keuangan perlu diperhatikan";
            description.textContent =
                "Pengeluaran mulai perlu diperhatikan. Evaluasi kebutuhan sebelum melakukan transaksi berikutnya.";
        } else if (status.toLowerCase() === "berlebihan") {
            title.textContent = "Pengeluaran melewati batas aman";
            description.textContent =
                "Kurangi pengeluaran yang tidak mendesak dan prioritaskan kebutuhan utama.";
        } else {
            title.textContent = "Status keuangan diperbarui";
            description.textContent =
                "Periksa hasil analisis keuangan untuk mengetahui kondisi terkini.";
        }

        document.getElementById("dashboard-analysis-time").textContent =
            "Diperbarui: " + new Date().toLocaleTimeString("id-ID");

    } catch (error) {
        console.warn("Analisis Fuzzy belum tersedia:", error);

        if (fuzzyMessage) {
            fuzzyMessage.textContent =
                "Analisis belum tersedia. Pastikan pengaturan anggaran sudah dibuat.";
            fuzzyMessage.style.color = "#ffc857";
        }

        document.getElementById("dashboard-fuzzy-status").textContent =
            "Belum tersedia";

        document.getElementById("dashboard-fuzzy-score").textContent =
            "-";

        document.getElementById("dashboard-health-title").textContent =
            "Menunggu data keuangan";

        document.getElementById("dashboard-health-description").textContent =
            "Atur anggaran dan catat transaksi untuk mendapatkan analisis kondisi keuangan.";

        document.getElementById("health-indicator").dataset.status =
            "belum tersedia";
    }
}

/* =========================================
   TOMBOL ANALISIS MANUAL
========================================= */

const analyzeButton = document.getElementById("analyze-button");

if (analyzeButton) {
    analyzeButton.addEventListener("click", runFuzzyAnalysis);
}

/* =========================================
   INISIALISASI MYFINANCE
========================================= */

async function initializeMyFinance() {
    setupMoneyInputs();

    setToday();

    await Promise.all([
        loadSummary(),
        loadTransactions(),
        loadBudget()
    ]);

    await runFuzzyAnalysis();

    showView("dashboard");
}

initializeMyFinance();
