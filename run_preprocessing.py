import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import pandas as pd
from preprocess import get_config, preprocess_document_to_file, preprocess_text

ROOT = Path(__file__).resolve().parent
REQUIRED = {"document_id", "judul_perda", "nomor_perda", "tahun_perda", "isi_dokumen"}


def write_atomic(path: Path, contents: str):
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(contents, encoding="utf-8")
    os.replace(temp, path)


def run(input_csv: Path, output_dir: Path, limit=None):
    if not input_csv.is_file():
        raise FileNotFoundError(f"Dataset tidak ditemukan: {input_csv}")
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_csv, dtype=str, keep_default_na=False, low_memory=False)
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError(f"Kolom wajib hilang: {sorted(missing)}")
    if df.empty or (df["document_id"].str.strip() == "").any():
        raise ValueError("Dataset kosong atau memiliki document_id kosong.")
    if df["document_id"].duplicated().any():
        bad = df.loc[df["document_id"].duplicated(keep=False), "document_id"].tolist()
        raise ValueError(f"Document ID duplikat: {bad[:10]}")

    if limit is not None:
        if limit < 1:
            raise ValueError("--limit harus lebih dari nol.")
        df = df.head(limit).copy()

    config = get_config()
    source_hash = hashlib.sha256(input_csv.read_bytes()).hexdigest()
    code_hash = hashlib.sha256((ROOT / "preprocess.py").read_bytes()).hexdigest()[:12]
    config["dataset_sha256"] = source_hash
    config["preprocess_script_sha256_prefix"] = code_hash
    config["jumlah_dokumen"] = int(len(df))
    config["source_column"] = "isi_dokumen"
    config["target_column"] = "teks_preprocessed"
    fingerprint = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:12]

    cache_dir = output_dir / "cache" / fingerprint
    cache_dir.mkdir(parents=True, exist_ok=True)

    print(f"Dataset      : {input_csv}", flush=True)
    print(f"Dokumen      : {len(df)}", flush=True)
    print(f"Total karakter: {df['isi_dokumen'].map(len).sum():,}", flush=True)
    print(f"Folder output: {output_dir}", flush=True)
    print(f"Judul kosong : {df['judul_perda'].str.strip().eq('').sum()}", flush=True)
    for suspect in ("PERDA_2025_UNKNOWN_ed89a575", "PERDA_2019_3"):
        if suspect in set(df["document_id"]):
            print(f"PERINGATAN: validasi dokumen {suspect} sebelum evaluasi akhir.", flush=True)

    reports = []
    processed_texts = []
    for ix, (_, row) in enumerate(df.iterrows(), start=1):
        doc_id = row["document_id"]
        stem = hashlib.sha256(doc_id.encode("utf-8")).hexdigest()[:24]
        text_file = cache_dir / f"{stem}.txt"
        stats_file = cache_dir / f"{stem}.json"
        if text_file.is_file() and stats_file.is_file():
            stats = json.loads(stats_file.read_text(encoding="utf-8"))
            state = "CACHE"
        else:
            temporary = text_file.with_name(text_file.name + ".tmp")
            stats = preprocess_document_to_file(row["isi_dokumen"], temporary)
            os.replace(temporary, text_file)
            write_atomic(stats_file, json.dumps(stats, ensure_ascii=False, indent=2))
            state = "BARU"

        processed = text_file.read_text(encoding="utf-8")
        processed_texts.append(processed)
        reports.append({
            "document_id": doc_id,
            "tahun_perda": row["tahun_perda"],
            "judul_perda": row["judul_perda"],
            "status_review_asli": row.get("status_review", ""),
            "jumlah_karakter_asli": len(row["isi_dokumen"]),
            **stats,
            "status_proses": state,
        })
        print(f"[{ix:03d}/{len(df):03d}] {doc_id} | {state} | {stats['jumlah_token_final']:,} token", flush=True)

    result = df.copy()
    result["teks_preprocessed"] = processed_texts

    final_empty = int(result["teks_preprocessed"].str.strip().eq("").sum())
    if final_empty:
        print(f"PERINGATAN: {final_empty} hasil preprocessing kosong, perlu ditinjau.", flush=True)

    index_cols = [col for col in [
        "document_id", "judul_perda", "nomor_perda", "tahun_perda", "sumber_file",
        "status_review", "path_pdf", "teks_preprocessed"
    ] if col in result.columns]

    result.to_csv(output_dir / "dataset_perda_preprocessed.csv", index=False, encoding="utf-8-sig")
    result[index_cols].to_csv(output_dir / "dataset_perda_untuk_tfidf.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(reports).to_csv(output_dir / "laporan_preprocessing.csv", index=False, encoding="utf-8-sig")
    write_atomic(output_dir / "konfigurasi_preprocessing.json", json.dumps(config, ensure_ascii=False, indent=2))

    print("\n=== SELESAI TAHAP 2 ===", flush=True)
    print(f"Dokumen di output   : {len(result)}", flush=True)
    print(f"Teks yang tidak kosong: {len(result) - final_empty}", flush=True)
    print(f"Output              : {output_dir}", flush=True)
    print("Uji query           :", preprocess_text("perlindungan dan pemberdayaan petani"), flush=True)
    return result


def main():
    p = argparse.ArgumentParser(description="Preprocessing lokal PERDAFIND untuk VS Code")
    p.add_argument("--input", type=Path, default=ROOT / "data" / "dataset_perda_100_terbaru.csv")
    p.add_argument("--output-dir", type=Path, default=ROOT / "outputs")
    p.add_argument("--limit", type=int, help="Untuk uji cepat: proses N dokumen pertama")
    args = p.parse_args()
    try:
        run(args.input.resolve(), args.output_dir.resolve(), args.limit)
    except Exception as err:
        print(f"ERROR: {type(err).__name__}: {err}", file=sys.stderr)
        raise SystemExit(1) from err


if __name__ == "__main__":
    main()
