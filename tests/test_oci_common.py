"""
Testes de oci_common com o SDK `oci` mockado (ver conftest.py).

Cobrem, sem credenciais nem rede:
    - chat() com família Cohere (CohereChatRequest + extração de .text)
    - chat() com família Llama/Generic (GenericChatRequest + choices[...])
    - embed() em lotes (respeitando o limite de 96 por chamada)
    - exigência de OCI_COMPARTMENT_ID
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import oci_common  # noqa: E402
from conftest import resposta_cohere, resposta_embed, resposta_generic  # noqa: E402


class FakeClient:
    """Client de mentira que registra os detalhes recebidos e devolve respostas."""

    def __init__(self, resposta_chat=None, embeddings=None):
        self._resposta_chat = resposta_chat
        self._embeddings = embeddings or []
        self.chamadas_chat = []
        self.chamadas_embed = []

    def chat(self, detalhes):
        self.chamadas_chat.append(detalhes)
        return self._resposta_chat

    def embed_text(self, detalhes):
        self.chamadas_embed.append(detalhes)
        # Devolve um embedding por input recebido neste lote.
        n = len(detalhes.inputs)
        return resposta_embed(self._embeddings[:n] or [[0.0]] * n)


def _patch_client(monkeypatch, client):
    monkeypatch.setattr(oci_common, "get_client",
                        lambda: (client, {"region": "sa-saopaulo-1"}))


def test_chat_cohere_extrai_texto(monkeypatch, compartimento):
    client = FakeClient(resposta_chat=resposta_cohere("resposta cohere"))
    _patch_client(monkeypatch, client)

    out = oci_common.chat("oi", modelo="cohere.command-r-plus")

    assert out == {"texto": "resposta cohere", "modelo": "cohere.command-r-plus"}
    # Confere que montou um CohereChatRequest com a mensagem certa.
    req = client.chamadas_chat[0].chat_request
    assert req.message == "oi"


def test_chat_llama_extrai_texto(monkeypatch, compartimento):
    client = FakeClient(resposta_chat=resposta_generic("resposta llama"))
    _patch_client(monkeypatch, client)

    out = oci_common.chat("oi", modelo="meta.llama-3-70b-instruct")

    assert out["texto"] == "resposta llama"
    # Família Generic monta 'messages', não 'message'.
    req = client.chamadas_chat[0].chat_request
    assert hasattr(req, "messages")


def test_embed_respeita_lotes_de_96(monkeypatch, compartimento):
    # 100 textos -> 2 chamadas (96 + 4); 100 vetores no total.
    client = FakeClient(embeddings=[[float(i)] for i in range(100)])
    _patch_client(monkeypatch, client)

    vetores = oci_common.embed([f"t{i}" for i in range(100)])

    assert len(client.chamadas_embed) == 2
    assert len(client.chamadas_embed[0].inputs) == 96
    assert len(client.chamadas_embed[1].inputs) == 4
    assert len(vetores) == 100


def test_compartment_id_obrigatorio(monkeypatch):
    monkeypatch.delenv("OCI_COMPARTMENT_ID", raising=False)
    client = FakeClient(resposta_chat=resposta_cohere("x"))
    _patch_client(monkeypatch, client)

    with pytest.raises(RuntimeError, match="OCI_COMPARTMENT_ID"):
        oci_common.chat("oi")
