"""
Testes do pipeline de RAG com faiss fake e OCI mockado.

Cobrem, sem credenciais nem o pacote faiss instalado:
    - carregar_chunks(): lê e fatia os runbooks reais de data/runbooks
    - construir_indice(): chama embed() e popula o índice
    - consultar(): recupera trechos e monta o prompt fundamentado, chamando chat()
"""
import sys
import types
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


# --------------------------------------------------------------------------- #
# Fake do faiss (similaridade por produto interno, via numpy)                  #
# --------------------------------------------------------------------------- #
def _instalar_fake_faiss():
    faiss = types.ModuleType("faiss")

    def normalize_L2(x):  # noqa: N802 — mantém o nome da API real
        normas = np.linalg.norm(x, axis=1, keepdims=True)
        normas[normas == 0] = 1.0
        x /= normas

    class IndexFlatIP:
        def __init__(self, dim):
            self.dim = dim
            self._vetores = np.empty((0, dim), dtype="float32")

        def add(self, matriz):
            self._vetores = np.vstack([self._vetores, matriz])

        def search(self, q, k):
            scores = q @ self._vetores.T          # (1, n)
            ids = np.argsort(-scores, axis=1)[:, :k]
            dist = np.take_along_axis(scores, ids, axis=1)
            return dist, ids

    faiss.normalize_L2 = normalize_L2
    faiss.IndexFlatIP = IndexFlatIP
    sys.modules["faiss"] = faiss


_instalar_fake_faiss()

import oci_rag  # noqa: E402  (depois do fake faiss)


@pytest.fixture
def sem_cache(tmp_path, monkeypatch):
    """Aponta o cache do índice para um arquivo temporário (não polui o repo)."""
    monkeypatch.setattr(oci_rag, "CACHE", tmp_path / "idx.pkl")


def test_carregar_chunks_le_runbooks():
    chunks = oci_rag.carregar_chunks()
    assert len(chunks) > 0
    # Todo chunk tem fonte (.md) e texto não vazio.
    assert all(c["fonte"].endswith(".md") and c["texto"] for c in chunks)
    # O runbook de failover do RDS está entre as fontes.
    fontes = {c["fonte"] for c in chunks}
    assert "rds-failover.md" in fontes


def test_construir_e_consultar(monkeypatch, sem_cache):
    chunks = oci_rag.carregar_chunks()

    # embed() devolve um vetor determinístico por texto (dimensão 8).
    def fake_embed(textos, modelo=None):
        rng = np.random.default_rng(0)
        return [rng.random(8).tolist() for _ in textos]

    capturado = {}

    def fake_chat(prompt, modelo=None, max_tokens=600, temperatura=0.3):
        capturado["prompt"] = prompt
        return {"texto": "resposta do RAG", "modelo": "cohere.command-r-plus"}

    monkeypatch.setattr(oci_rag, "embed", fake_embed)
    monkeypatch.setattr(oci_rag, "chat", fake_chat)

    indice, chunks2 = oci_rag.construir_indice()
    assert indice.dim == 8
    assert len(chunks2) == len(chunks)
    assert oci_rag.CACHE.exists()  # cache foi gravado

    resposta = oci_rag.consultar("Como fazer failover do RDS?", indice, chunks2)
    assert resposta == "resposta do RAG"
    # O prompt enviado ao modelo deve conter contexto recuperado e a pergunta.
    assert "Contexto" in capturado["prompt"]
    assert "failover do RDS" in capturado["prompt"]


def test_carregar_indice_usa_cache(monkeypatch, sem_cache):
    def fake_embed(textos, modelo=None):
        return [[1.0, 0.0, 0.0] for _ in textos]

    monkeypatch.setattr(oci_rag, "embed", fake_embed)

    # Primeira chamada constrói e grava o cache.
    oci_rag.construir_indice()
    # embed não deve ser chamado de novo ao carregar do cache.
    monkeypatch.setattr(oci_rag, "embed",
                        lambda *a, **k: pytest.fail("embed não deveria rodar"))
    indice, chunks = oci_rag.carregar_indice()
    assert indice.dim == 3
    assert len(chunks) > 0
