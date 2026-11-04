import joblib
import numpy as np
from scipy.sparse import save_npz
from sklearn.feature_extraction.text import TfidfVectorizer
from pathlib import Path

import pandas as pd


# 1. Menentukan lokasi project
ROOT = Path(__file__).resolve().parent

INPUT_FILE = ROOT / "outputs" / "dataset_perda_untuk_tfidf.csv"


def main():
    # 2. Memastikan file dataset tersedia
    if not INPUT_FILE.is_file():
        raise FileNotFoundError(
            f"Dataset tidak ditemukan: {INPUT_FILE}"
        )

    # 3. Membaca dataset
    print("Membaca dataset...")
    df = pd.read_csv(
        INPUT_FILE,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
    )

    # 4. Memvalidasi kolom yang dibutuhkan
    required_columns = {
        "document_id",
        "judul_perda",
        "teks_preprocessed",
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            f"Kolom wajib tidak ditemukan: {sorted(missing)}"
        )

    # 5. Menampilkan ringkasan dataset
    print("\n=== VALIDASI DATASET ===")
    print(f"Jumlah dokumen : {len(df)}")
    print(f"Jumlah kolom   : {len(df.columns)}")
    print(
        "Teks kosong    : "
        f"{df['teks_preprocessed'].str.strip().eq('').sum()}"
    )
    print("\nContoh judul dokumen:")
    print(df["judul_perda"].head().to_string(index=False))

    
    
    # 6. Menyiapkan dokumen untuk TF-IDF
    documents = df["teks_preprocessed"].tolist()

    # 7. Membuat TF-IDF Vectorizer
    vectorizer = TfidfVectorizer(
        lowercase=False,
        token_pattern=r"(?u)\b\w+\b",
        norm="l2",
        use_idf=True,
        smooth_idf=True,
        dtype=np.float64,
    )

    # 8. Menghitung bobot TF-IDF dan membangun matriks
    print("\nMembangun matriks TF-IDF...")
    tfidf_matrix = vectorizer.fit_transform(documents)

    # 9. Menyiapkan lokasi output
    output_dir = ROOT / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 10. Menyimpan matriks TF-IDF
    matrix_path = output_dir / "tfidf_matrix.npz"
    save_npz(matrix_path, tfidf_matrix)

    # 11. Menyimpan vectorizer dan vocabulary
    vectorizer_path = output_dir / "tfidf_vectorizer.joblib"
    joblib.dump(vectorizer, vectorizer_path)

    # 12. Menampilkan ringkasan hasil
    print("\n=== HASIL TF-IDF ===")
    print(f"Jumlah dokumen : {tfidf_matrix.shape[0]}")
    print(f"Jumlah fitur   : {tfidf_matrix.shape[1]}")
    print(f"Bobot nonzero  : {tfidf_matrix.nnz:,}")
    print(f"Ukuran matriks : {tfidf_matrix.shape}")
    print(f"Matriks disimpan: {matrix_path}")
    print(f"Vectorizer disimpan: {vectorizer_path}")

    print("\nValidasi dataset berhasil.")


if __name__ == "__main__":
    main()
