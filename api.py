from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Literal

import pandas as pd
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field, field_validator
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer

from cos_similarity import load_tfidf_artifacts, search_perda


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
        )
        for rank, result in enumerate(ranked_results[:payload.limit], start=1)
    ]
    return SearchResponse(
        query=payload.query,
        total=len(results),
        results=results,
    )
