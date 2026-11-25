
# ==========================================
# FUZZY MAMDANI - MYFINANCE
# ==========================================

# Fungsi keanggotaan segitiga
def triangular(x, a, b, c):
    if x <= a or x >= c:
        return 0.0

    if x == b:
        return 1.0

    if x < b:
        return (x - a) / (b - a)

    return (c - x) / (c - b)


# Fungsi keanggotaan trapesium
def trapezoidal(x, a, b, c, d):
    if x < a or x > d:
        return 0.0

    if b <= x <= c:
        return 1.0

    if a <= x < b:
        return (x - a) / (b - a)

    if c < x <= d:
        return (d - x) / (d - c)

    return 0.0


# Fuzzifikasi input rasio pengeluaran
def fuzzify_spending(x):
    x = max(0, min(x, 200))

    return {
        "rendah": trapezoidal(x, 0, 0, 50, 100),
        "sedang": triangular(x, 50, 100, 150),
        "tinggi": trapezoidal(x, 100, 150, 200, 200)
    }


# Fuzzifikasi input kecukupan saldo
def fuzzify_balance(x):
    x = max(0, min(x, 200))

    return {
        "sedikit": trapezoidal(x, 0, 0, 50, 100),
        "sedang": triangular(x, 50, 100, 150),
        "banyak": trapezoidal(x, 100, 150, 200, 200)
    }


# Fungsi keanggotaan output
def fuzzify_output(z):
    return {
        "aman": trapezoidal(z, 0, 0, 20, 40),
        "waspada": triangular(z, 25, 50, 75),
        "berlebihan": trapezoidal(z, 60, 80, 100, 100)
    }


# Inferensi dan agregasi Mamdani
def mamdani_inference(spending, balance):

    rules = [
        ("rendah", "sedikit", "waspada"),
        ("rendah", "sedang", "aman"),
        ("rendah", "banyak", "aman"),

        ("sedang", "sedikit", "berlebihan"),
        ("sedang", "sedang", "waspada"),
        ("sedang", "banyak", "aman"),

        ("tinggi", "sedikit", "berlebihan"),
        ("tinggi", "sedang", "berlebihan"),
        ("tinggi", "banyak", "waspada")
    ]

    # Menghitung kekuatan setiap aturan
    rule_strengths = []

    for input1, input2, output in rules:
        alpha = min(
            spending[input1],
            balance[input2]
        )

        rule_strengths.append({
            "output": output,
            "alpha": alpha
        })

    # Agregasi menggunakan MAX
    aggregated = []

    step = 0.1
    z = 0.0

    while z <= 100:
        output_membership = fuzzify_output(z)

        values = []

        for rule in rule_strengths:
            clipped = min(
                rule["alpha"],
                output_membership[rule["output"]]
            )

            values.append(clipped)

        aggregated.append(max(values))
        z += step

    # Defuzzifikasi menggunakan Centroid
    numerator = 0.0
    denominator = 0.0

    for i, membership in enumerate(aggregated):
        z_value = i * step

        numerator += z_value * membership
        denominator += membership

    if denominator == 0:
        score = 0.0
    else:
        score = numerator / denominator

    return score, rule_strengths


# Fungsi utama analisis keuangan
def analyze_finances(
    spending_today,
    daily_budget,
    current_balance,
    remaining_days
):

    if daily_budget <= 0:
        raise ValueError("Anggaran harian harus lebih dari 0")

    if remaining_days <= 0:
        raise ValueError("Sisa hari harus lebih dari 0")

    if spending_today < 0 or current_balance < 0:
        raise ValueError("Pengeluaran dan saldo tidak boleh negatif")

    # Menghitung rasio pengeluaran
    spending_ratio = (
        spending_today / daily_budget
    ) * 100

    # Menghitung kebutuhan dana sampai akhir periode
    expected_funds = daily_budget * remaining_days

    # Menghitung rasio kecukupan saldo
    balance_ratio = (
        current_balance / expected_funds
    ) * 100

    # Fuzzifikasi
    spending_membership = fuzzify_spending(spending_ratio)
    balance_membership = fuzzify_balance(balance_ratio)

    # Inferensi dan defuzzifikasi
    score, rules = mamdani_inference(
        spending_membership,
        balance_membership
    )

    # Menentukan status berdasarkan skor
    if score <= 40:
        status = "Aman"
    elif score <= 60:
        status = "Waspada"
    else:
        status = "Berlebihan"

    return {
        "rasio_pengeluaran": round(spending_ratio, 2),
        "rasio_kecukupan_saldo": round(balance_ratio, 2),
        "nilai_fuzzy": round(score, 2),
        "status": status,
        "keanggotaan_pengeluaran": spending_membership,
        "keanggotaan_saldo": balance_membership,
        "aturan_aktif": [
            rule for rule in rules if rule["alpha"] > 0
        ]
    }
