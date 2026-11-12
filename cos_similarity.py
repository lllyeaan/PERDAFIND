
import joblib
import numpy as np
import pandas as pd

from pathlib import Path
from scipy.sparse import load_npz
from sklearn.metrics.pairwise import cosine_similarity as cosine_sim

from preprocess import preprocess_text


# 1. Menentukan lokasi project
ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "outputs"

MATRIX_FILE = OUTPUT_DIR / "tfidf_matrix.npz"
VECTORIZER_FILE = OUTPUT_DIR / "tfidf_vectorizer.joblib"
DATASET_FILE = OUTPUT_DIR / "dataset_perda_untuk_tfidf.csv"


# 2. Memuat hasil pembentukan TF-IDF
def load_tfidf_artifacts():

    required_files = [
        MATRIX_FILE,
        VECTORIZER_FILE,
        DATASET_FILE,
    ]

    for file in required_files:
        if not file.is_file():
            raise FileNotFoundError(
                f"File tidak ditemukan: {file}"
            )

    # Memuat matriks TF-IDF
    tfidf_matrix = load_npz(MATRIX_FILE)

    # Memuat vectorizer TF-IDF
    vectorizer = joblib.load(VECTORIZER_FILE)

    # Memuat metadata dokumen Perda
    documents = pd.read_csv(
        DATASET_FILE,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
    )

    # Validasi kesesuaian matriks dan dataset
    if tfidf_matrix.shape[0] != len(documents):
        raise ValueError(
            "Jumlah baris matriks TF-IDF tidak sesuai "
            "dengan jumlah dokumen."
        )

    if tfidf_matrix.shape[1] != len(
        vectorizer.get_feature_names_out()
    ):
        raise ValueError(
            "Jumlah fitur matriks tidak sesuai "
            "dengan vocabulary vectorizer."
        )

    required_columns = {
        "document_id",
        "judul_perda",
        "nomor_perda",
        "tahun_perda",
    }

    missing_columns = required_columns - set(documents.columns)

    if missing_columns:
        raise ValueError(
            f"Kolom metadata tidak ditemukan: {sorted(missing_columns)}"
        )

    return tfidf_matrix, vectorizer, documents


# 3. Melakukan pencarian dokumen Perda
def search_perda(
    query,
    tfidf_matrix,
    vectorizer,
    documents,
):

    if not query.strip():
        raise ValueError("Query tidak boleh kosong.")

    # Preprocessing query
    processed_query = preprocess_text(query)

    print(f"\nQuery asli          : {query}")
    print(f"Query preprocessing : {processed_query}")

    if not processed_query:
        print("\nQuery tidak menghasilkan token.")
        return []

    # Mengambil kata-kata hasil preprocessing
    query_terms = list(dict.fromkeys(processed_query.split()))

    # Memeriksa kata query yang tersedia dalam vocabulary
    available_terms = [
        term for term in query_terms
        if term in vectorizer.vocabulary_
    ]

    if not available_terms:
        print(
            "\nTidak ada kata dalam query yang ditemukan "
            "pada vocabulary dokumen."
        )
        return []

    if len(available_terms) < len(query_terms):
        missing_terms = set(query_terms) - set(available_terms)
        print(
            f"\nKata tidak ditemukan dalam vocabulary: "
            f"{', '.join(sorted(missing_terms))}"
        )
        print("Pencarian dilanjutkan menggunakan kata yang tersedia.")

    # Mengubah query menjadi vektor TF-IDF
    processed_available_query = " ".join(available_terms)
    query_vector = vectorizer.transform([processed_available_query])

    if query_vector.nnz == 0:
        print("\nQuery tidak menghasilkan vektor TF-IDF.")
        return []

    # Bandingkan dengan seluruh dokumen agar kecocokan sebagian tetap diranking.
    similarity_scores = cosine_sim(query_vector, tfidf_matrix).flatten()

    # Mengurutkan skor dari tertinggi ke terendah
    ranked_indices = np.argsort(
        -similarity_scores,
        kind="stable"
    )

    similarity_scores = similarity_scores[ranked_indices]

    results = []

    # Mengambil seluruh dokumen yang lolos filter AND
    for index, score in zip(ranked_indices, similarity_scores):

        if score <= 0:
            continue

        document = documents.iloc[index]

        # Menangani metadata yang kosong
        judul = document["judul_perda"].strip()
        nomor = document["nomor_perda"].strip()
        tahun = document["tahun_perda"].strip()

        results.append({
            "document_id": document["document_id"],
            "judul_perda": judul or "Judul tidak tersedia",
            "nomor_perda": nomor or "Tidak tersedia",
            "tahun_perda": tahun or "Tidak tersedia",
            "similarity": float(score),
        })

    return results


# 4. Menampilkan hasil pencarian
def display_results(results):

    print("\n========== HASIL PENCARIAN PERDA ==========")

    if not results:
        print("Tidak ditemukan dokumen yang relevan.")
        return

    print(f"Jumlah dokumen ditemukan: {len(results)}")

    for rank, result in enumerate(results, start=1):

        print(f"\nPeringkat        : {rank}")
        print(f"ID Dokumen       : {result['document_id']}")
        print(f"Judul Perda      : {result['judul_perda']}")
        print(f"Nomor Perda      : {result['nomor_perda']}")
        print(f"Tahun Perda      : {result['tahun_perda']}")
        print(
            f"Cosine Similarity: "
            f"{result['similarity']:.6f}"
        )

    print("\n===========================================")


# 5. Input query dengan tombol ESC
def get_query():
    import msvcrt

    print(
        "\nMasukkan kata kunci (tekan ESC untuk keluar): ",
        end="",
        flush=True
    )

    query = ""

    while True:

        char = msvcrt.getwch()

        # Keluar jika tombol ESC ditekan
        if char == "\x1b":
            print("\n\nProgram pencarian selesai.")
            return None

        # Memproses tombol Enter
        elif char == "\r":
            print()
            return query

        # Memproses tombol Backspace
        elif char == "\b":
            if query:
                query = query[:-1]
                print("\b \b", end="", flush=True)

        # Mengabaikan tombol khusus lainnya
        elif char in ("\x00", "\xe0"):
            msvcrt.getwch()

        # Memasukkan karakter ke query
        else:
            query += char
            print(char, end="", flush=True)


# 6. Program utama
def main():

    try:

        # Memuat hasil TF-IDF
        tfidf_matrix, vectorizer, documents = load_tfidf_artifacts()

        print("=== PERDAFIND: PENCARIAN DOKUMEN ===")

        while True:

            query = get_query()

            # Menghentikan program jika ESC ditekan
            if query is None:
                break

            try:

                results = search_perda(
                    query,
                    tfidf_matrix,
                    vectorizer,
                    documents,
                )

                display_results(results)

            except ValueError as err:
                print(f"\nInput tidak valid: {err}")

    except Exception as err:

        print(f"\nERROR: {type(err).__name__}: {err}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
