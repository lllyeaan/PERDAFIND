# PERDAFIND

PERDAFIND adalah aplikasi pencarian dokumen Peraturan Daerah (Perda). Query
pengguna diproses dengan preprocessing yang sama seperti dokumen, diubah menjadi
vektor TF-IDF, lalu dibandingkan dengan dokumen menggunakan cosine similarity.
Hasil ditampilkan dari skor tertinggi ke terendah. Dokumen yang cocok dengan
sebagian kata query tetap dapat ditemukan.

## Fitur

- Pencarian Perda berdasarkan kata kunci.
- Ranking hasil berdasarkan cosine similarity.
- REST API FastAPI dan UI web yang disajikan dari server yang sama.
- Pratinjau PDF di browser jika file PDF tersedia.

## Struktur proyek

| Path | Keterangan |
| --- | --- |
| `api.py` | FastAPI, endpoint pencarian, health check, dan penyajian PDF |
| `preprocess.py` | Preprocessing teks query dan dokumen |
| `run_preprocessing.py` | Membuat dataset teks hasil preprocessing |
| `tfidf.py` | Melatih vectorizer dan menyimpan matriks TF-IDF |
| `cos_similarity.py` | Memuat artefak dan mencari/ranking dokumen |
| `static/` | UI web: HTML, CSS, dan JavaScript |
| `data/` | Dataset sumber |
| `outputs/` | Dataset hasil preprocessing, laporan, dan artefak model |
| `documents/` | File PDF yang dapat dibuka dari UI |

## Persiapan lokal (Windows)

Buka PowerShell di folder proyek, lalu buat virtual environment dan instal
dependensi:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Menyiapkan dataset dan model

Dataset sumber default adalah `data/dataset_perda_100_terbaru.csv`.

1. Jalankan preprocessing semua dokumen:

   ```powershell
   .\.venv\Scripts\python.exe .\run_preprocessing.py
   ```

   Proses ini membuat `outputs/dataset_perda_untuk_tfidf.csv` dan laporan
   preprocessing lainnya.

2. Buat matriks dan vectorizer TF-IDF:

   ```powershell
   .\.venv\Scripts\python.exe .\tfidf.py
   ```

   Artefak yang dibuat adalah:

   - `outputs/tfidf_matrix.npz`
   - `outputs/tfidf_vectorizer.joblib`

   Kedua file tersebut diabaikan Git dan perlu dibuat ulang di lingkungan baru.

Untuk uji cepat, preprocessing dapat dibatasi:

```powershell
.\.venv\Scripts\python.exe .\run_preprocessing.py --limit 2
```

`--limit 2` mengganti dataset indeks dengan dua dokumen pertama. Jalankan kembali
preprocessing tanpa `--limit`, lalu `tfidf.py`, sebelum menjalankan pencarian
dengan dataset lengkap.

## Menjalankan website dan API

Jalankan server dari folder proyek:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api:app --reload
```

Buka:

- Website: <http://127.0.0.1:8000/>
- Dokumentasi interaktif API: <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/health>

UI dan API menggunakan origin yang sama, sehingga konfigurasi CORS tidak
diperlukan untuk penggunaan ini.

## Endpoint API

### `GET /health`

Contoh respons:

```json
{
  "status": "ok",
  "document_count": 100
}
```

### `POST /search`

Request:

```json
{
  "query": "perlindungan petani",
  "limit": 10
}
```

`query` wajib berisi 1–500 karakter setelah spasi di awal dan akhir dihapus.
`limit` bernilai 1–100 dan default-nya 10.

Respons berisi daftar hasil berperingkat. `document_url` berisi tautan PDF jika
PDF lokal tersedia; nilainya `null` jika file belum tersedia.

```json
{
  "query": "perlindungan petani",
  "total": 1,
  "results": [
    {
      "rank": 1,
      "document_id": "PERDA_2019_2",
      "judul_perda": "PERLINDUNGAN DAN PEMBERDAYAAN PETANI",
      "nomor_perda": "2",
      "tahun_perda": "2019",
      "similarity": 0.715,
      "document_url": "/documents/PERDA_2019_2"
    }
  ]
}
```

`total` adalah jumlah hasil yang dikembalikan setelah batas `limit` diterapkan.
Query yang tidak menemukan dokumen menghasilkan respons sukses dengan daftar
`results` kosong. Input tidak valid menghasilkan HTTP 422.

## Menambahkan dan membuka PDF

Letakkan PDF yang ingin dibuka langsung di folder `documents/`. Nama file harus
sama dengan nama file pada bagian akhir kolom `path_pdf` di
`outputs/dataset_perda_untuk_tfidf.csv`. Contoh:

```text
documents/PERDA_NO_8_TAHUN_2025_INOVASI_DAERAH.pdf
```

Jangan gunakan nama path Google Drive/Colab sebagai lokasi file di komputer.
Aplikasi hanya menggunakan nama file PDF dari dataset dan mencarinya di folder
`documents/`. API menyediakan PDF melalui `GET /documents/{document_id}` dan
mengirimkannya agar dapat dibuka langsung di browser. Jika file tidak ada, UI
menampilkan “PDF belum tersedia”.

File PDF diabaikan Git karena ukurannya besar. Saat ini koleksi lokal berukuran
sekitar 1,47 GB; file tersebut harus disediakan secara terpisah saat deployment.

## Deployment di Render

1. Push source code dan `outputs/dataset_perda_untuk_tfidf.csv` ke repository
   GitHub. Jangan commit PDF besar atau artefak `.npz`/`.joblib`; model dibuat
   ulang pada proses build.
2. Di Render, pilih **New → Web Service**, lalu hubungkan repository.
3. Gunakan konfigurasi berikut:

   | Pengaturan | Nilai |
   | --- | --- |
   | Language | Python 3 |
   | Build Command | `pip install -r requirements.txt && python tfidf.py` |
   | Start Command | `uvicorn api:app --host 0.0.0.0 --port $PORT` |

4. Tambahkan persistent disk pada layanan berbayar dengan mount path:

   ```text
   /opt/render/project/src/documents
   ```

   Path ini sesuai dengan lokasi `documents/` pada layanan Python Render.
   Pilih ukuran disk yang cukup untuk seluruh PDF dan pertumbuhan berikutnya.
5. Setelah deploy, salin PDF ke disk tersebut menggunakan transfer file melalui
   Shell/SCP Render. Pertahankan nama file yang sesuai dengan kolom `path_pdf`.
6. Buka URL layanan Render dan uji `/health`, pencarian, lalu tombol **Buka
   dokumen PDF**. Pastikan PDF dikirim sebagai `application/pdf`.

Filesystem layanan Render bersifat sementara tanpa persistent disk, dan paket
Free tidak mendukung persistent disk. Karena itu, PDF yang disimpan di sana
tidak cocok untuk layanan Free atau penyimpanan jangka panjang.

Referensi resmi:

- [Deploy FastAPI di Render](https://render.com/docs/deploy-fastapi)
- [Persistent disk Render](https://render.com/docs/disks)
- [Batasan layanan Free Render](https://render.com/docs/free)
