from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, Literal
from urllib.parse import quote

import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer

from cos_similarity import load_tfidf_artifacts, search_perda

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
DOCUMENTS_DIR = ROOT / "documents"


@dataclass
class SearchIndex:
    tfidf_matrix: csr_matrix
    vectorizer: TfidfVectorizer
    documents: pd.DataFrame


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    tfidf_matrix, vectorizer, documents = load_tfidf_artifacts()
    app.state.search_index = SearchIndex(
        tfidf_matrix=tfidf_matrix,
        vectorizer=vectorizer,
        documents=documents,
    )
    yield


app = FastAPI(
    title="PERDAFIND Search API",
    description="REST API pencarian dokumen Peraturan Daerah.",
    version="1.0.0",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=10, ge=1, le=100)

    @field_validator("query", mode="before")
    @classmethod
    def strip_query(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Query harus berupa teks.")
        return value.strip()


class SearchResult(BaseModel):
    rank: int
    document_id: str
    judul_perda: str
    nomor_perda: str
    tahun_perda: str
    similarity: float
    document_url: str | None


class SearchResponse(BaseModel):
    query: str
    total: int
    results: list[SearchResult]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    document_count: int


@app.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    index: SearchIndex = request.app.state.search_index
    return HealthResponse(
        status="ok",
        document_count=len(index.documents),
    )


def find_document_pdf(documents: pd.DataFrame, document_id: str) -> Path | None:
    matching_documents = documents.loc[
        documents["document_id"] == document_id
    ]
    if matching_documents.empty or "path_pdf" not in documents.columns:
        return None

    source_path = str(matching_documents.iloc[0]["path_pdf"]).strip()
    filename = Path(source_path.replace("\\", "/")).name
    if not filename or Path(filename).suffix.lower() != ".pdf":
        return None

    documents_root = DOCUMENTS_DIR.resolve()
    pdf_path = (documents_root / filename).resolve()
    if pdf_path.parent != documents_root or not pdf_path.is_file():
        return None

    return pdf_path


@app.post("/search", response_model=SearchResponse)
def search(payload: SearchRequest, request: Request) -> SearchResponse:
    index: SearchIndex = request.app.state.search_index
    ranked_results = search_perda(
        payload.query,
        index.tfidf_matrix,
        index.vectorizer,
        index.documents,
    )
    results = [
        SearchResult(
            rank=rank,
            document_id=result["document_id"],
            judul_perda=result["judul_perda"],
            nomor_perda=result["nomor_perda"],
            tahun_perda=result["tahun_perda"],
            similarity=result["similarity"],
            document_url=(
                f"/documents/{quote(result['document_id'], safe='')}"
                if find_document_pdf(index.documents, result["document_id"])
                else None
            ),
        )
        for rank, result in enumerate(ranked_results[:payload.limit], start=1)
    ]
    return SearchResponse(
        query=payload.query,
        total=len(results),
        results=results,
    )


@app.get("/documents/{document_id}", include_in_schema=False)
def open_document(document_id: str, request: Request) -> FileResponse:
    index: SearchIndex = request.app.state.search_index
    pdf_path = find_document_pdf(index.documents, document_id)
    if pdf_path is None:
        raise HTTPException(
            status_code=404,
            detail="PDF dokumen tidak ditemukan. Pastikan PDF tersedia di folder documents.",
        )

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=pdf_path.name,
        content_disposition_type="inline",
    )
