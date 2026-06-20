"""
oci_rag.py — RAG (Retrieval-Augmented Generation) usando serviços OCI.

Pipeline:
    1. Lê os runbooks em data/runbooks/*.md
    2. Quebra em trechos (chunks) e gera embeddings com OCI GenAI Embeddings
       (oci.generative_ai_inference -> embed_text, cohere.embed-multilingual-v3.0)
    3. Indexa os vetores localmente em FAISS (IndexFlatIP, similaridade de cosseno)
    4. Na consulta: embeda a pergunta, recupera os top-k trechos e pede ao
       OCI GenAI (Cohere Command R+) uma resposta fundamentada nos trechos.

Os mesmos runbooks dos projetos anteriores são reutilizados (failover do RDS,
VPC, ECS, incidentes de segurança, etc.).

Uso:
    python src/oci_rag.py "Como fazer failover do RDS?"
    python src/oci_rag.py --rebuild "Como fazer failover do RDS?"

Custo: US$ 0,00 dentro dos limites Always Free.
"""
from __future__ import annotations

import argparse
import pickle
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

from oci_common import chat, embed

load_dotenv()

RAIZ = Path(__file__).resolve().parent.parent
RUNBOOKS = RAIZ / "data" / "runbooks"
CACHE = RAIZ / "data" / "faiss_index.pkl"
TOP_K = 4
TAM_CHUNK = 800  # caracteres por trecho


def carregar_chunks() -> list[dict]:
    """Lê os runbooks e os fatia em trechos com metadado de origem."""
    chunks: list[dict] = []
    for arquivo in sorted(RUNBOOKS.glob("*.md")):
        texto = arquivo.read_text(encoding="utf-8")
        for i in range(0, len(texto), TAM_CHUNK):
            trecho = texto[i:i + TAM_CHUNK].strip()
            if trecho:
                chunks.append({"fonte": arquivo.name, "texto": trecho})
    return chunks


def construir_indice():
    """Gera embeddings via OCI e monta o índice FAISS, com cache em disco."""
    import faiss

    chunks = carregar_chunks()
    if not chunks:
        raise RuntimeError(f"Nenhum runbook encontrado em {RUNBOOKS}")

    print(f"Gerando embeddings de {len(chunks)} trechos via OCI GenAI...")
    vetores = embed([c["texto"] for c in chunks])
    matriz = np.array(vetores, dtype="float32")
    faiss.normalize_L2(matriz)  # normaliza para usar produto interno = cosseno

    indice = faiss.IndexFlatIP(matriz.shape[1])
    indice.add(matriz)

    CACHE.write_bytes(pickle.dumps({"chunks": chunks, "matriz": matriz}))
    print(f"Índice salvo em {CACHE}")
    return indice, chunks


def carregar_indice():
    """Recupera o índice do cache ou o reconstrói se ainda não existir."""
    import faiss

    if CACHE.exists():
        dados = pickle.loads(CACHE.read_bytes())
        indice = faiss.IndexFlatIP(dados["matriz"].shape[1])
        indice.add(dados["matriz"])
        return indice, dados["chunks"]
    return construir_indice()


def consultar(pergunta: str, indice, chunks) -> str:
    """Recupera trechos relevantes e gera resposta fundamentada via OCI GenAI."""
    import faiss

    q = np.array(embed([pergunta]), dtype="float32")
    faiss.normalize_L2(q)
    _, ids = indice.search(q, TOP_K)

    contexto = "\n\n".join(
        f"[{chunks[i]['fonte']}]\n{chunks[i]['texto']}" for i in ids[0]
    )
    prompt = (
        "Você é um SRE sênior. Responda à pergunta usando SOMENTE o contexto "
        "abaixo, extraído dos runbooks internos. Se a resposta não estiver no "
        "contexto, diga isso claramente. Cite o nome do runbook usado.\n\n"
        f"### Contexto\n{contexto}\n\n### Pergunta\n{pergunta}\n\n### Resposta"
    )
    return chat(prompt, max_tokens=700)["texto"]


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG com OCI Generative AI")
    parser.add_argument("pergunta", help="pergunta sobre os runbooks")
    parser.add_argument("--rebuild", action="store_true",
                        help="recria o índice (re-embeda os runbooks)")
    args = parser.parse_args()

    indice, chunks = construir_indice() if args.rebuild else carregar_indice()
    print("\n" + consultar(args.pergunta, indice, chunks))


if __name__ == "__main__":
    main()
