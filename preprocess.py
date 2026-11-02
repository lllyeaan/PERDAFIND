import re
import unicodedata
from functools import lru_cache
from importlib.metadata import version

from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory

# Kata-kata ini penting dalam dokumen hukum dan tidak dihapus sebagai stopword.
PROTECTED_TERMS = frozenset({
    "tidak", "bukan", "belum", "tanpa", "jangan", "kecuali",
    "wajib", "harus", "dilarang", "larang", "hak", "izin",
    "pajak", "retribusi", "peraturan", "perda", "daerah",
    "kabupaten", "banyuwangi",
})

STOPWORDS = frozenset(StopWordRemoverFactory().get_stop_words()) - PROTECTED_TERMS
STEMMER = StemmerFactory().create_stemmer()


@lru_cache(maxsize=250_000)
def stem_word(word: str) -> str:
    return STEMMER.stem(word)


def case_folding(text: str) -> str:
    return unicodedata.normalize("NFKC", str(text)).casefold()


def cleaning(text: str) -> str:
    text = re.sub(r"(?<=[a-z])-\s*\r?\n\s*(?=[a-z])", "", text)
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"[^a-z\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokenizing(text: str):
    return (match.group(0) for match in re.finditer(r"[a-z]{2,}", text))


def stopword_removal(tokens):
    return (token for token in tokens if token not in STOPWORDS)


def stemming(tokens):
    return (stem_word(token) for token in tokens)


def preprocess_text(text: str) -> str:
    """Satu fungsi untuk memproses query saat pencarian di website."""
    folded = case_folding(text)
    cleaned = cleaning(folded)
    tokens = tokenizing(cleaned)
    without_stopwords = stopword_removal(tokens)
    stemmed = stemming(without_stopwords)
    return " ".join(t for t in stemmed if len(t) >= 2)


def preprocess_document_to_file(text: str, destination):
    folded = case_folding(text)
    cleaned = cleaning(folded)
    before = 0
    after_stopwords = 0
    after_stemming = 0
    distinct_terms = set()
    buffer = []
    first = True
    output_chars = 0

    with open(destination, "w", encoding="utf-8") as handle:
        for word in tokenizing(cleaned):
            before += 1
            if word in STOPWORDS:
                continue
            after_stopwords += 1
            base = stem_word(word)
            if len(base) < 2:
                continue
            after_stemming += 1
            distinct_terms.add(base)
            buffer.append(base)
            if len(buffer) >= 10_000:
                chunk = " ".join(buffer)
                prefix = " " if not first else ""
                handle.write(prefix + chunk)
                output_chars += len(prefix) + len(chunk)
                first = False
                buffer.clear()

        if buffer:
            chunk = " ".join(buffer)
            prefix = " " if not first else ""
            handle.write(prefix + chunk)
            output_chars += len(prefix) + len(chunk)

    return {
        "jumlah_token_awal": before,
        "jumlah_token_setelah_stopword": after_stopwords,
        "jumlah_token_final": after_stemming,
        "jumlah_term_unik": len(distinct_terms),
        "panjang_teks_hasil": output_chars,
        "reduksi_token_persen": round(100 * (1 - after_stemming / max(1, before)), 2),
    }


def get_config():
    return {
        "versi_preprocessing": "perdafind-tahap2-vscode-1",
        "sastrawi": version("Sastrawi"),
        "urutan": ["case_folding", "cleaning", "tokenizing", "stopword_removal", "stemming"],
        "case_folding": "Unicode NFKC dan casefold",
        "cleaning": "gabung pemenggalan baris, hapus URL, angka, simbol dan spasi berlebih",
        "min_panjang_token": 2,
        "stopword_source": "Sastrawi, tanpa protected_terms",
        "protected_terms": sorted(PROTECTED_TERMS),
        "stemming": "Sastrawi StemmerFactory",
        "catatan": "Gunakan fungsi preprocess_text yang sama untuk query ketika website berjalan",
    }
