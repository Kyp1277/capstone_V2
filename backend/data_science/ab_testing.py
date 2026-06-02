"""
A/B Testing Simulator - Python Implementation
Menguji signifikansi statistik performa Model AI CV Matcher Lama (A) vs Model AI Baru (B).
Metrik: Conversion Rate (Match Satisfaction Rate) pengguna saat menggunakan sistem.
"""

import math


def perform_ab_test(n_a, conversions_a, n_b, conversions_b, alpha=0.05):
    # Rates
    p_a = conversions_a / n_a
    p_b = conversions_b / n_b

    print("=" * 60)
    print("             A/B TESTING REPORT IN PYTHON")
    print("=" * 60)
    print(f"Kelompok A (Model Lama)   : N = {n_a:<6} | Sukses = {conversions_a:<5} | Rate = {p_a * 100:.2f}%")
    print(f"Kelompok B (Model AI Baru): N = {n_b:<6} | Sukses = {conversions_b:<5} | Rate = {p_b * 100:.2f}%")
    print("-" * 60)

    # Pooled probability
    p_pooled = (conversions_a + conversions_b) / (n_a + n_b)

    # Standard error pooled
    se_pooled = math.sqrt(p_pooled * (1 - p_pooled) * (1 / n_a + 1 / n_b))

    # Z-Score
    try:
        z_score = (p_b - p_a) / se_pooled
    except ZeroDivisionError:
        z_score = 0.0

    # P-Value approximation (Two-tailed)
    # Using standard error function (erf) approximation
    def norm_cdf(z):
        return (1.0 + math.erf(z / math.sqrt(2.0))) / 2.0

    p_value = 2 * (1 - norm_cdf(abs(z_score)))

    print(f"Statistik Z-Score   : {z_score:.4f}")
    print(f"Nilai Probabilitas P: {p_value:.6f}")
    print(f"Tingkat Signifikansi: {alpha}")
    print("-" * 60)

    # Hypothesis Testing
    if p_value < alpha:
        print("HASIL: SIGNIFIKAN SECARA STATISTIK (Tolak Hipotesis Nol H0)")
        print("Kesimpulan: Model AI Baru (B) secara signifikan terbukti meningkatkan")
        print("            kepuasan pengguna dibandingkan Model Lama (A).")
        print("STATUS KELAYAKAN: REKOMENDASI DEPLOY KE PRODUCTION!")
    else:
        print("HASIL: TIDAK SIGNIFIKAN (Gagal menolak Hipotesis Nol H0)")
        print("Kesimpulan: Perbedaan performa antara kelompok A dan B kemungkinan")
        print("            besar hanya karena variasi acak (noise).")
        print("STATUS KELAYAKAN: PERLU PENELITIAN LEBIH LANJUT / UJI ULANG.")

    print("=" * 60)


if __name__ == "__main__":
    # Contoh data simulasi
    # Kelompok A: 5000 pengguna, 3710 menyatakan puas (74.2%)
    # Kelompok B: 5200 pengguna, 4045 menyatakan puas (77.8%)
    perform_ab_test(n_a=5000, conversions_a=3710, n_b=5200, conversions_b=4045)
