
const rupiah = (angka) => {
    return new Intl.NumberFormat("id-ID", {
        style: "currency",
        currency: "IDR",
        maximumFractionDigits: 0
    }).format(angka || 0);
};


// Mengambil ringkasan keuangan
async function loadSummary() {
    try {
        const response = await fetch("/api/summary");

        if (!response.ok) {
            throw new Error("Gagal mengambil ringkasan");
        }

        const data = await response.json();

        document.getElementById("saldo").textContent =
            rupiah(data.saldo);

        document.getElementById("pemasukan").textContent =
            rupiah(data.total_pemasukan);

        document.getElementById("pengeluaran").textContent =
            rupiah(data.total_pengeluaran);

    } catch (error) {
        console.error(error);
    }
}


// Mengambil riwayat transaksi
async function loadTransactions() {
    const list = document.getElementById("transaction-list");

    try {
        const response = await fetch("/api/transactions");

        if (!response.ok) {
            throw new Error("Gagal mengambil transaksi");
        }

        const transactions = await response.json();

        list.innerHTML = "";

        if (transactions.length === 0) {
            list.innerHTML = `
                <tr>
                    <td colspan="5">Belum ada transaksi.</td>
                </tr>
            `;
            return;
        }

        transactions.forEach((item) => {
            const row = document.createElement("tr");

            const date = document.createElement("td");
            date.textContent = item.transaction_date;

            const category = document.createElement("td");
            category.textContent = item.category;

            const type = document.createElement("td");
            type.textContent = item.type;
            type.className = item.type === "pemasukan"
                ? "income" : "expense";

            const amount = document.createElement("td");
            amount.textContent = rupiah(item.amount);
            amount.className = type.className;

            // Membuat tombol hapus
            const action = document.createElement("td");
            const deleteButton = document.createElement("button");

            deleteButton.textContent = "Hapus";
            deleteButton.type = "button";
            deleteButton.className = "delete-button";

            deleteButton.addEventListener("click", () => {
                deleteTransaction(item.id);
            });

            action.appendChild(deleteButton);

            row.append(date, category, type, amount, action);
            list.appendChild(row);
        });

    } catch (error) {
        console.error(error);

        list.innerHTML = `
            <tr>
                <td colspan="5">Gagal memuat transaksi.</td>
            </tr>
        `;
    }
}


// Menghapus transaksi
async function deleteTransaction(id) {
    const confirmation = confirm(
        "Apakah kamu yakin ingin menghapus transaksi ini?"
    );

    if (!confirmation) {
        return;
    }

    try {
        const response = await fetch(
            `/api/transactions/${id}`,
            {
                method: "DELETE"
            }
        );

        const result = await response.json();

        if (!response.ok) {
            throw new Error(
                result.detail || "Gagal menghapus transaksi"
            );
        }

        alert("Transaksi berhasil dihapus.");

        // Memperbarui data setelah transaksi dihapus
        await loadTransactions();
        await loadSummary();

    } catch (error) {
        alert(error.message);
        console.error(error);
    }
}


// Menambahkan transaksi
document.getElementById("transaction-form")
    .addEventListener("submit", async (event) => {

        event.preventDefault();

        const message = document.getElementById("form-message");

        const transaction = {
            type: document.getElementById("type").value,
            category: document.getElementById("category").value,
            amount: Number(document.getElementById("amount").value),
            description: document.getElementById("description").value,
            transaction_date:
                document.getElementById("transaction-date").value
        };

        try {
            const response = await fetch("/api/transactions", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(transaction)
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(
                    result.detail || "Gagal menyimpan transaksi"
                );
            }

            message.textContent = "Transaksi berhasil disimpan!";
            message.style.color = "green";

            
// Menambahkan transaksi dengan validasi input
document.getElementById("transaction-form")
    .addEventListener("submit", async (event) => {

        event.preventDefault();

        const message = document.getElementById("form-message");

        const type = document.getElementById("type").value;
        const category = document.getElementById("category").value;
        const amount = Number(
            document.getElementById("amount").value
        );
        const description =
            document.getElementById("description").value;
        const transactionDate =
            document.getElementById("transaction-date").value;

        // Validasi jenis transaksi
        if (!type) {
            message.textContent = "Silakan pilih jenis transaksi.";
            message.style.color = "red";
            return;
        }

        // Validasi kategori
        if (!category) {
            message.textContent = "Silakan pilih kategori transaksi.";
            message.style.color = "red";
            return;
        }

        // Validasi nominal
        if (!Number.isFinite(amount) || amount <= 0) {
            message.textContent =
                "Nominal transaksi harus lebih dari Rp0.";
            message.style.color = "red";
            return;
        }

        // Validasi tanggal
        if (!transactionDate) {
            message.textContent = "Tanggal transaksi wajib diisi.";
            message.style.color = "red";
            return;
        }

        const transaction = {
            type: type,
            category: category,
            amount: amount,
            description: description,
            transaction_date: transactionDate
        };

        try {
            const response = await fetch("/api/transactions", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(transaction)
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(
                    result.detail || "Gagal menyimpan transaksi"
                );
            }

            message.textContent = "Transaksi berhasil disimpan!";
            message.style.color = "green";

            document.getElementById("transaction-form").reset();
            setToday();

            await loadSummary();
            await loadTransactions();

        } catch (error) {
            message.textContent = error.message;
            message.style.color = "red";
        }
    });



// Mengatur tanggal hari ini
function setToday() {
    const today = new Date();

    const localDate = new Date(
        today.getTime() - today.getTimezoneOffset() * 60000
    ).toISOString().slice(0, 10);

    document.getElementById("transaction-date").value = localDate;
}


// Menampilkan atau menyembunyikan input anggaran manual
const budgetMode = document.getElementById("budget-mode");
const manualBudgetField = document.getElementById("manual-budget-field");

budgetMode.addEventListener("change", function () {
    if (budgetMode.value === "manual") {
        manualBudgetField.classList.remove("hidden");
    } else {
        manualBudgetField.classList.add("hidden");
    }
});


// Memuat data anggaran dari API
async function loadBudget() {
    try {
        const response = await fetch("/api/budgets");
        const data = await response.json();

        if (data.daily_budget === undefined) {
            return;
        }

        document.getElementById("budget-initial").textContent =
            rupiah(data.initial_balance);

        document.getElementById("daily-budget").textContent =
            rupiah(data.daily_budget);

        document.getElementById("budget-mode-result").textContent =
            data.budget_mode === "otomatis" ? "Otomatis" : "Manual";

        // Mengisi kembali form dengan data terakhir
        document.getElementById("initial-balance").value =
            data.initial_balance;

        document.getElementById("fixed-expenses").value =
            data.fixed_expenses;

        document.getElementById("savings-target").value =
            data.savings_target;

        document.getElementById("start-date").value =
            data.start_date;

        document.getElementById("end-date").value =
            data.end_date;

        document.getElementById("budget-mode").value =
            data.budget_mode;

        if (data.budget_mode === "manual") {
            manualBudgetField.classList.remove("hidden");

            document.getElementById("manual-daily-budget").value =
                data.daily_budget;
        } else {
            manualBudgetField.classList.add("hidden");
        }

    } catch (error) {
        console.error("Gagal memuat anggaran:", error);
    }
}



// Menyimpan pengaturan anggaran dengan validasi
document.getElementById("budget-form")
    .addEventListener("submit", async function (event) {

        event.preventDefault();

        const message = document.getElementById("budget-message");

        const initialBalance = Number(
            document.getElementById("initial-balance").value
        );

        const fixedExpenses = Number(
            document.getElementById("fixed-expenses").value
        );

        const savingsTarget = Number(
            document.getElementById("savings-target").value
        );

        const startDate =
            document.getElementById("start-date").value;

        const endDate =
            document.getElementById("end-date").value;

        const manualDailyBudget = Number(
            document.getElementById("manual-daily-budget").value
        );

        // Validasi saldo awal
        if (
            document.getElementById("initial-balance").value === "" ||
            !Number.isFinite(initialBalance) ||
            initialBalance <= 0
        ) {
            message.textContent =
                "Saldo awal harus lebih dari Rp0.";
            message.style.color = "red";
            return;
        }

        // Validasi pengeluaran tetap
        if (
            !Number.isFinite(fixedExpenses) ||
            fixedExpenses < 0
        ) {
            message.textContent =
                "Pengeluaran tetap tidak boleh negatif.";
            message.style.color = "red";
            return;
        }

        // Validasi target tabungan
        if (
            !Number.isFinite(savingsTarget) ||
            savingsTarget < 0
        ) {
            message.textContent =
                "Target tabungan tidak boleh negatif.";
            message.style.color = "red";
            return;
        }

        // Validasi tanggal
        if (!startDate || !endDate) {
            message.textContent =
                "Tanggal mulai dan tanggal akhir wajib diisi.";
            message.style.color = "red";
            return;
        }

        if (endDate < startDate) {
            message.textContent =
                "Tanggal akhir tidak boleh lebih awal dari tanggal mulai.";
            message.style.color = "red";
            return;
        }

        // Validasi anggaran manual
        if (
            budgetMode.value === "manual" &&
            (
                !Number.isFinite(manualDailyBudget) ||
                manualDailyBudget <= 0
            )
        ) {
            message.textContent =
                "Anggaran harian manual harus lebih dari Rp0.";
            message.style.color = "red";
            return;
        }

        const payload = {
            initial_balance: initialBalance,
            fixed_expenses: fixedExpenses,
            savings_target: savingsTarget,
            start_date: startDate,
            end_date: endDate,
            budget_mode: budgetMode.value,
            manual_daily_budget: budgetMode.value === "manual"
                ? manualDailyBudget
                : null
        };

        try {
            const response = await fetch("/api/budgets", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(
                    result.detail || "Gagal menyimpan anggaran"
                );
            }

            message.textContent =
                "Anggaran berhasil disimpan. Anggaran harian: " +
                rupiah(result.daily_budget);

            message.style.color = "green";

            await loadBudget();
            await loadSummary();

        } catch (error) {
            message.textContent = error.message;
            message.style.color = "red";
        }
    });



// Menjalankan fungsi saat halaman dibuka
setToday();
loadSummary();
loadTransactions();
loadBudget();


// Menjalankan analisis Fuzzy Mamdani
async function runFuzzyAnalysis() {
    const button = document.getElementById("analyze-button");
    const message = document.getElementById("fuzzy-message");

    button.disabled = true;
    button.textContent = "Menganalisis...";

    try {
        const response = await fetch("/api/fuzzy-analysis");
        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail || "Analisis gagal dilakukan"
            );
        }

        const analysis = data.analisis_fuzzy;

        // Menampilkan nilai fuzzy
        document.getElementById("fuzzy-score").textContent =
            analysis.nilai_fuzzy;

        // Menampilkan status keuangan
        const statusElement = document.getElementById("fuzzy-status");
        statusElement.textContent = analysis.status;

        statusElement.style.color =
            analysis.status === "Aman" ? "#16a34a" :
            analysis.status === "Waspada" ? "#d97706" :
            "#dc2626";

        // Menampilkan detail analisis
        document.getElementById("spending-ratio").textContent =
            analysis.rasio_pengeluaran + "%";

        document.getElementById("balance-ratio").textContent =
            analysis.rasio_kecukupan_saldo + "%";

        document.getElementById("remaining-days").textContent =
            data.sisa_hari + " hari";

        message.textContent =
            "Analisis berhasil diperbarui pada " +
            data.tanggal_analisis;

    } catch (error) {
        message.textContent = error.message;

    } finally {
        button.disabled = false;
        button.textContent = "Analisis Keuangan";
    }
}


// Menghubungkan tombol dengan fungsi analisis
document.getElementById("analyze-button")
    .addEventListener("click", runFuzzyAnalysis);
