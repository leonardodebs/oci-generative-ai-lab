"""
quality.py — Heurística simples de qualidade (1-5) por cobertura de palavras-chave.

Não substitui avaliação humana; serve para comparar respostas de forma
reproduzível e barata entre nuvens, usando os mesmos critérios para todas.
"""
from __future__ import annotations

# Palavras-chave esperadas por prompt (mesma base do lab GCP, ordem dos prompts).
ESPERADO = [
    ["nat", "internet gateway", "privada", "saída", "público"],
    ["exposição", "porta", "security group", "ssh", "público", "iam"],
    ["boto3", "ec2", "stopped", "describe_instances", "filter"],
    ["kubernetes", "ecs", "fargate", "produção", "escala"],
    ["rto", "rpo", "tempo", "recuperação", "dados"],
]


def nota_qualidade(resposta: str, idx_prompt: int) -> int:
    """Devolve nota 1-5 pela fração de palavras-chave cobertas na resposta."""
    if idx_prompt >= len(ESPERADO):
        return 3  # prompt fora da lista padrão: nota neutra
    termos = ESPERADO[idx_prompt]
    texto = (resposta or "").lower()
    acertos = sum(1 for t in termos if t in texto)
    fracao = acertos / len(termos)
    # Mapeia 0..1 para 1..5 (sempre ao menos 1).
    return max(1, round(fracao * 5))


def contar_tokens(texto: str) -> int:
    """Estimativa grosseira de tokens (~4 chars/token) quando o SDK não informa."""
    return max(1, len(texto or "") // 4)
