"""
conftest.py — Infraestrutura de testes sem nuvem.

O SDK `oci` (e opcionalmente `faiss`) pode não estar instalado no ambiente de
CI/portfólio. Aqui injetamos *fakes* leves em sys.modules ANTES de qualquer
import dos módulos sob teste, para que `import oci` / `import faiss` resolvam
para nossas implementações de mentira. Assim cobrimos a lógica de oci_common
(chat Cohere x Llama, embeddings em lotes) e do RAG sem credenciais reais.
"""
import sys
import types
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))


# --------------------------------------------------------------------------- #
# Fake do SDK `oci`                                                            #
# --------------------------------------------------------------------------- #
class _ModeloGenerico:
    """Substitui qualquer classe de model do SDK: guarda os kwargs recebidos."""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _ModelsModule(types.ModuleType):
    """Devolve _ModeloGenerico para qualquer nome de classe acessado."""

    # Constante usada por GenericChatRequest no código real.
    API_FORMAT_GENERIC = "GENERIC"

    def __getattr__(self, nome):
        if nome == "BaseChatRequest":
            # BaseChatRequest.API_FORMAT_GENERIC é lido no oci_common.
            base = types.SimpleNamespace(API_FORMAT_GENERIC="GENERIC")
            return base
        return _ModeloGenerico


def _instalar_fake_oci():
    """Monta a árvore de módulos fake do `oci` em sys.modules."""
    oci = types.ModuleType("oci")

    # oci.config
    config_mod = types.ModuleType("oci.config")
    config_mod.from_file = lambda **kw: {"region": "sa-saopaulo-1"}
    config_mod.validate_config = lambda cfg: None
    oci.config = config_mod

    # oci.retry
    retry_mod = types.ModuleType("oci.retry")
    retry_mod.NoneRetryStrategy = lambda *a, **k: None
    oci.retry = retry_mod

    # oci.generative_ai_inference + .models
    gai = types.ModuleType("oci.generative_ai_inference")
    gai.GenerativeAiInferenceClient = lambda *a, **k: None
    models = _ModelsModule("oci.generative_ai_inference.models")
    gai.models = models
    oci.generative_ai_inference = gai

    sys.modules["oci"] = oci
    sys.modules["oci.config"] = config_mod
    sys.modules["oci.retry"] = retry_mod
    sys.modules["oci.generative_ai_inference"] = gai
    sys.modules["oci.generative_ai_inference.models"] = models


# Instala o fake imediatamente no import do conftest (antes dos testes).
if "oci" not in sys.modules:
    _instalar_fake_oci()


# --------------------------------------------------------------------------- #
# Helpers reutilizáveis pelos testes                                           #
# --------------------------------------------------------------------------- #
def resposta_cohere(texto: str):
    """Imita resp.data.chat_response.text (família Cohere)."""
    chat_response = types.SimpleNamespace(text=texto)
    data = types.SimpleNamespace(chat_response=chat_response)
    return types.SimpleNamespace(data=data)


def resposta_generic(texto: str):
    """Imita resp.data.chat_response.choices[0].message.content[0].text (Llama)."""
    content = [types.SimpleNamespace(text=texto)]
    message = types.SimpleNamespace(content=content)
    choices = [types.SimpleNamespace(message=message)]
    chat_response = types.SimpleNamespace(choices=choices)
    data = types.SimpleNamespace(chat_response=chat_response)
    return types.SimpleNamespace(data=data)


def resposta_embed(vetores):
    """Imita resp.data.embeddings."""
    data = types.SimpleNamespace(embeddings=vetores)
    return types.SimpleNamespace(data=data)


@pytest.fixture
def compartimento(monkeypatch):
    """Garante OCI_COMPARTMENT_ID definido para as chamadas dos testes."""
    monkeypatch.setenv("OCI_COMPARTMENT_ID", "ocid1.compartment.oc1..teste")
