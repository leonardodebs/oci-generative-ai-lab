"""
server.py — Backend Flask para o mini-app de chat do OCI Generative AI.

Por que um backend? As credenciais OCI (~/.oci/config) NUNCA podem ir para o
navegador. O front estático fala com este servidor, que faz a chamada ao
OCI GenAI usando o SDK no lado seguro.

Endpoints:
    GET  /                -> serve o front estático (web/index.html)
    GET  /api/health      -> status do ambiente OCI (sem expor segredos)
    POST /api/chat        -> { "prompt": "...", "model": "..." }
    POST /api/rag         -> { "pergunta": "..." }

Uso:
    python src/server.py            # http://127.0.0.1:5000
    make serve

Custo: US$ 0,00 — apenas roteia para o OCI GenAI dentro do Always Free.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

from oci_common import MODELO_CHAT, chat

load_dotenv()

RAIZ = Path(__file__).resolve().parent.parent
WEB = RAIZ / "web"

app = Flask(__name__, static_folder=None)

# Índice do RAG é caro de montar: carregamos sob demanda e memoizamos.
_rag_cache: dict = {}


def _erro(msg: str, status: int = 400):
    return jsonify({"erro": msg}), status


@app.get("/")
def index():
    return send_from_directory(WEB, "index.html")


@app.get("/<path:arquivo>")
def estaticos(arquivo: str):
    """Serve style.css, app.js, etc. da pasta web/."""
    return send_from_directory(WEB, arquivo)


@app.get("/api/health")
def health():
    """Diz se o ambiente parece configurado, sem revelar segredos."""
    config_ok = (Path.home() / ".oci" / "config").exists()
    comp_ok = bool(os.getenv("OCI_COMPARTMENT_ID"))
    pronto = config_ok and comp_ok
    return jsonify({
        "pronto": pronto,
        "config_oci": config_ok,
        "compartment_id": comp_ok,
        "modelo_padrao": MODELO_CHAT,
    })


@app.post("/api/chat")
def api_chat():
    dados = request.get_json(silent=True) or {}
    prompt = (dados.get("prompt") or "").strip()
    if not prompt:
        return _erro("campo 'prompt' é obrigatório")
    modelo = dados.get("model") or MODELO_CHAT

    try:
        inicio = time.perf_counter()
        resultado = chat(prompt, modelo=modelo)
        latencia = round(time.perf_counter() - inicio, 3)
    except Exception as exc:  # noqa: BLE001 — devolve erro estruturado ao front
        return _erro(f"falha na inferência: {exc}", 500)

    return jsonify({**resultado, "latencia_s": latencia})


@app.post("/api/rag")
def api_rag():
    dados = request.get_json(silent=True) or {}
    pergunta = (dados.get("pergunta") or "").strip()
    if not pergunta:
        return _erro("campo 'pergunta' é obrigatório")

    try:
        import oci_rag

        if "indice" not in _rag_cache:
            _rag_cache["indice"], _rag_cache["chunks"] = oci_rag.carregar_indice()
        inicio = time.perf_counter()
        resposta = oci_rag.consultar(
            pergunta, _rag_cache["indice"], _rag_cache["chunks"])
        latencia = round(time.perf_counter() - inicio, 3)
    except Exception as exc:  # noqa: BLE001
        return _erro(f"falha no RAG: {exc}", 500)

    return jsonify({"texto": resposta, "latencia_s": latencia})


if __name__ == "__main__":
    porta = int(os.getenv("PORT", "5000"))
    app.run(host="127.0.0.1", port=porta, debug=True)
