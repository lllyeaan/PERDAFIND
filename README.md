1. Jalankan
py -m venv .venv


2. Instal dependency 

.\.venv\Scripts\python.exe -m pip install -r requirements.txt


3. Uji dengan dataset kecl (opsional)

.\.venv\Scripts\python.exe run_preprocessing.py --limit 2


4. Jalankan semua dokumen:

.\.venv\Scripts\python.exe run_preprocessing.py

