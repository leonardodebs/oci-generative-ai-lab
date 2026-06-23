"""
Testes do backend Flask (src/server.py) com o OCI mockado.

Usam o test client do Flask — sem subir servidor, sem rede, sem credenciais.
Pulam automaticamente se o Flask não estiver instalado no ambiente.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

pytest.importorskip("flask", reason="Flask não instalado (pip install flask)")

import server  # noqa: E402


@pytest.fixture
def client():
    server.app.config.update(TESTING=True)
    return server.app.test_client()


def test_health_responde_json(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    dados = resp.get_json()
    # Campos esperados existem (valores dependem do ambiente).
    assert "pronto" in dados and "modelo_padrao" in dados


def test_chat_sem_prompt_retorna_400(client):
    resp = client.post("/api/chat", json={})
    assert resp.status_code == 400
    assert "erro" in resp.get_json()


def test_chat_chama_oci_e_devolve_texto(client, monkeypatch):
    chamado = {}

    def fake_chat(prompt, modelo=None, max_tokens=600, temperatura=0.3):
        chamado["prompt"] = prompt
        chamado["modelo"] = modelo
        return {"texto": "olá do OCI", "modelo": modelo or "cohere.command-r-plus"}

    monkeypatch.setattr(server, "chat", fake_chat)

    resp = client.post("/api/chat",
                       json={"prompt": "oi", "model": "meta.llama-3-70b-instruct"})
    assert resp.status_code == 200
    dados = resp.get_json()
    assert dados["texto"] == "olá do OCI"
    assert "latencia_s" in dados
    assert chamado["prompt"] == "oi"
    assert chamado["modelo"] == "meta.llama-3-70b-instruct"


def test_chat_propaga_erro_da_inferencia(client, monkeypatch):
    def fake_chat(*a, **k):
        raise RuntimeError("endpoint indisponível")

    monkeypatch.setattr(server, "chat", fake_chat)

    resp = client.post("/api/chat", json={"prompt": "oi"})
    assert resp.status_code == 500
    assert "endpoint indisponível" in resp.get_json()["erro"]


def test_rag_sem_pergunta_retorna_400(client):
    resp = client.post("/api/rag", json={})
    assert resp.status_code == 400
