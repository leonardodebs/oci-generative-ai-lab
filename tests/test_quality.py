"""Testes da heurística de qualidade e da contagem de tokens (sem nuvem)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from quality import contar_tokens, nota_qualidade  # noqa: E402


def test_nota_alta_quando_cobre_palavras_chave():
    resposta = ("NAT Gateway permite saída para a internet de sub-redes privada, "
                "enquanto o Internet Gateway expõe recursos público.")
    assert nota_qualidade(resposta, 0) >= 4


def test_nota_baixa_quando_resposta_irrelevante():
    assert nota_qualidade("texto totalmente fora do tema", 0) == 1


def test_indice_fora_da_lista_retorna_neutro():
    assert nota_qualidade("qualquer coisa", 99) == 3


def test_contar_tokens_aproxima_quatro_chars():
    assert contar_tokens("a" * 40) == 10
    assert contar_tokens("") == 1
