1. Jalankan
py -m venv .venv


2. Instal dependency 

.\.venv\Scripts\python.exe -m pip install -r requirements.txt


3. Uji dengan dataset kecl (opsional)

.\.venv\Scripts\python.exe run_preprocessing.py --limit 2


4. Jalankan semua dokumen:

.\.venv\Scripts\python.exe run_preprocessing.py


5. Siapkan artefak pencarian TF-IDF:

.\.venv\Scripts\python.exe tfidf.py


6. Gunakan fungsi pencarian dari aplikasi/server:

```python
from cos_similarity import load_tfidf_artifacts, search_perda

tfidf_matrix, vectorizer, documents = load_tfidf_artifacts()
results = search_perda(
    "perlindungan petani",
    tfidf_matrix,
    vectorizer,
    documents,
)
```

Muat artefak sekali saat aplikasi mulai, lalu gunakan kembali objek tersebut
untuk setiap request pencarian. `search_perda` mengembalikan daftar dokumen
relevan yang sudah diurutkan dan tidak menulis output ke terminal.
