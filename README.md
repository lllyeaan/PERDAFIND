# PERDAFIND — Tahap 2 Preprocessing (VS Code / Windows)

Program untuk **case folding → cleaning → tokenizing → stopword removal → stemming Sastrawi** dengan checkpoint per dokumen.
Tidak memakai Google Colab maupun Google Drive.

## Persiapan (terminal VS Code / PowerShell)

1. Ekstrak folder ini dan buka di VS Code.
2. Salin CSV hasil OCR ke: `data/dataset_perda_100_terbaru.csv`
3. Buat virtual environment:

```powershell
py -m venv .venv
```

4. Instal dependency tanpa perlu mengaktifkan virtualenv:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

5. Uji dengan dataset kecil (sebaiknya pilih dokumen pendek untuk pengujian):

```powershell
.\.venv\Scripts\python.exe run_preprocessing.py --limit 2
```

6. Jalankan semua dokumen:

```powershell
.\.venv\Scripts\python.exe run_preprocessing.py
```

**Catatan:** `--limit 2` mengambil dua dokumen pertama, yang dalam dataset saat ini mencakup dokumen 1.502 halaman. Untuk tes cepat, buat file CSV sampel dari 2–3 dokumen pendek atau lanjutkan langsung ke run penuh.

## Output

- `outputs/dataset_perda_preprocessed.csv`: semua kolom asli + `teks_preprocessed`.
- `outputs/dataset_perda_untuk_tfidf.csv`: kolom ringkas untuk tahap 3.
- `outputs/laporan_preprocessing.csv`: statistik token per dokumen.
- `outputs/konfigurasi_preprocessing.json`: konfigurasi untuk audit/reproduksibilitas.
- `outputs/cache/`: simpan hasil per dokumen agar run berikutnya melanjutkan tanpa mengulang dokumen berhasil.

## Perhatian

- Dua entri dari OCR sebelumnya (`PERDA_2025_UNKNOWN_ed89a575`, `PERDA_2019_3`) **tidak otomatis dihapus**. Pastikan validitas 100 dokumen sebelum evaluasi final.
- Angka dihapus dari **fitur teks** untuk mengikuti proposal, tetapi `nomor_perda` dan `tahun_perda` tetap disimpan sebagai metadata.
- Di tahap API website, **impor fungsi `preprocess_text()` dari `preprocess.py`**, agar preprocessing query sama dengan dokumen.
- Jika file CSV sumber diubah atau kode preprocessing diganti, cache dibuat ulang berdasarkan fingerprint.
- File `path_pdf` dari Colab masih merupakan path lokal Drive dan bukan URL yang bisa dibuka website. Siapkan `pdf_url` saat integrasi website.
