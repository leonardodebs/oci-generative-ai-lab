"""Testes das funções puras do comparador de 3 nuvens (sem chamar APIs)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import three_clouds_comparison as tc  # noqa: E402


def test_custo_1k_proporcional_aos_tokens():
    nome = "GCP Vertex (Gemini 1.5 Flash)"
    c1 = tc._custo_1k(nome, 100)
    c2 = tc._custo_1k(nome, 200)
    assert c2 > c1 > 0


def test_markdown_marca_provedor_indisponivel():
    agregado = {
        "OCI GenAI (Cohere Command R+)": {"disponivel": False, "motivo": "sem creds"},
    }
    md = tc.gerar_markdown(agregado, ["p1"])
    assert "indisponível" in md
    assert "| OCI GenAI" in md


def test_markdown_inclui_linha_disponivel():
    agregado = {
        "AWS Bedrock (Claude 3 Haiku)": {
            "disponivel": True, "latencia_media_s": 1.2,
            "qualidade_media": 4.0, "tokens_medios": 300, "custo_1k_usd": 0.225,
        },
    }
    md = tc.gerar_markdown(agregado, ["p1", "p2"])
    assert "0.225" in md
    assert "Prompts avaliados: **2**" in md
