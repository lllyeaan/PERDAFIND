from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from scipy.sparse import load_npz
from sklearn.metrics.pairwise import cosine_similarity
from preprocess import preprocess_text

# 1. KONFIGURASI PATH
ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "outputs"

MATRIX_FILE = OUTPUT_DIR / "tfidf_matrix.npz"
VECTORIZER_FILE = OUTPUT_DIR / "tfidf_vectorizer.joblib"
DATASET_FILE = OUTPUT_DIR / "dataset_perda_untuk_tfidf.csv"

TOP_K = [1, 3, 5, 10]

# 2. LOAD MODEL DAN DATASET
def load_model():
    matrix = load_npz(MATRIX_FILE)
    vectorizer = joblib.load(VECTORIZER_FILE)
    documents = pd.read_csv(DATASET_FILE)

    return matrix, vectorizer, documents

# 3. FUNGSI PENCARIAN
def search(query, matrix, vectorizer, documents):
    query_preprocessed = preprocess_text(query)

    if not query_preprocessed:
        return []

    query_vector = vectorizer.transform([query_preprocessed])

    vocabulary = vectorizer.vocabulary_

    query_terms = query_preprocessed.split()

    available_terms = [
        vocabulary[term]
        for term in query_terms
        if term in vocabulary
    ]

    if not available_terms:
        return []

    # Filter AND: dokumen harus mengandung seluruh
    # kata pencarian yang tersedia dalam vocabulary.
    candidate_mask = np.asarray(
        (matrix[:, available_terms] > 0).sum(axis=1)
    ).ravel() == len(available_terms)

    candidate_indices = np.where(candidate_mask)[0]

    if len(candidate_indices) == 0:
        return []

    candidate_matrix = matrix[candidate_indices]

    similarities = cosine_similarity(
        query_vector,
        candidate_matrix
    ).ravel()

    ranked_indices = np.argsort(similarities)[::-1]

    results = []

    for index in ranked_indices:
        document_index = candidate_indices[index]

        results.append({
            "document_index": document_index,
            "cosine_similarity": similarities[index]
        })

    return results

# 4. PERHITUNGAN METRIK EVALUASI
def calculate_metrics(ranked_results, relevant_document_id, documents):
    ranked_ids = [
        documents.iloc[result["document_index"]]["document_id"]
        for result in ranked_results
    ]

    evaluation_results = []

    for k in TOP_K:
        top_k_results = ranked_ids[:k]

        true_positive = (
            1 if relevant_document_id in top_k_results else 0
        )

        precision = true_positive / k
        recall = true_positive / 1

        if precision + recall == 0:
            f1 = 0
        else:
            f1 = (
                2 * precision * recall
                / (precision + recall)
            )

        evaluation_results.append({
            "top_k": k,
            "presisi": precision,
            "recall": recall,
            "f1_score": f1
        })

    return evaluation_results

# 5. PROSES EVALUASI MODEL
def main():
    matrix, vectorizer, documents = load_model()

    results = []
    query_sources = []

    print("EVALUASI MODEL PERDAFIND")

    print(f"Jumlah dokumen : {len(documents)}")

    for _, row in documents.iterrows():

        document_id = row["document_id"]
        judul_perda = row["judul_perda"]

        # Query menggunakan judul Perda.
        if pd.notna(judul_perda) and str(judul_perda).strip():
            query = str(judul_perda)
            query_source = "Judul Perda"

        # Jika judul kosong, gunakan lima kata awal
        # dari teks yang sudah dipreprocessing.
        else:
            teks = row["teks_preprocessed"]

            if pd.isna(teks) or not str(teks).strip():
                query = ""
            else:
                query = " ".join(str(teks).split()[:5])

            query_source = "Isi dokumen (5 kata awal)"

        query_sources.append(query_source)

        ranked_results = search(
            query,
            matrix,
            vectorizer,
            documents
        )

        metrics = calculate_metrics(
            ranked_results,
            document_id,
            documents
        )

        for metric in metrics:
            results.append({
                "document_id": document_id,
                "judul_perda": row["judul_perda"],
                "nomor_perda": row["nomor_perda"],
                "tahun_perda": row["tahun_perda"],
                "top_k": metric["top_k"],
                "presisi": metric["presisi"],
                "recall": metric["recall"],
                "f1_score": metric["f1_score"]
            })

    # 6. HASIL EVALUASI DETAIL
    detail_df = pd.DataFrame(results)

    detail_df = detail_df[
        [
            "document_id",
            "judul_perda",
            "nomor_perda",
            "tahun_perda",
            "top_k",
            "presisi",
            "recall",
            "f1_score"
        ]
    ]

    detail_path = OUTPUT_DIR / "hasil_evaluasi_detail.csv"
    detail_df.to_csv(detail_path, index=False)

    # 7. HASIL EVALUASI RATA-RATA
    summary_df = (
        detail_df
        .groupby("top_k")[["presisi", "recall", "f1_score"]]
        .mean()
        .reset_index()
    )

    summary_path = OUTPUT_DIR / "hasil_evaluasi.csv"
    summary_df.to_csv(summary_path, index=False)

    # 8. MENAMPILKAN HASIL
    print(f"Jumlah query   : {len(documents)}")

    print("\n          HASIL EVALUASI")
    print(summary_df.to_string(index=False))

    print("\nJumlah query berdasarkan sumber:")
    print(pd.Series(query_sources).value_counts().to_string())

    print("\nFile berhasil disimpan:")
    print(detail_path)
    print(summary_path)

if __name__ == "__main__":
    main()
