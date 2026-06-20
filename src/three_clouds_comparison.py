"""
three_clouds_comparison.py — Comparação final entre 3 nuvens de IA gerenciada.

Roda o mesmo prompt (ou os 5 prompts padrão) em cada provedor disponível:
    - AWS Bedrock    -> anthropic.claude-3-haiku
    - GCP Vertex AI  -> gemini-1.5-flash
    - OCI GenAI      -> cohere.command-r-plus

Mede latência, qualidade (1-5) e estima custo por 1.000 consultas com base nos
preços públicos por 1M de tokens. Cada nuvem ausente é simplesmente pulada,
então o relatório sai com 1, 2 ou 3 colunas conforme as credenciais presentes.

Saída:
    reports/three_clouds_ai_comparison.md  (tabela markdown)
    tabela resumida no terminal

Uso:
    python src/three_clouds_comparison.py
    python src/three_clouds_comparison.py "Explique NAT vs Internet Gateway"
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from oci_chat import PROMPTS_PADRAO
from quality import contar_tokens, nota_qualidade

load_dotenv()

RAIZ = Path(__file__).resolve().parent.parent
REPORTS = RAIZ / "reports"

# Preços públicos (US$ por 1M de tokens): entrada / saída.
PRECOS = {
    "AWS Bedrock (Claude 3 Haiku)": {"in": 0.25, "out": 1.25},
    "GCP Vertex (Gemini 1.5 Flash)": {"in": 0.075, "out": 0.30},
    "OCI GenAI (Cohere Command R+)": {"in": 0.50, "out": 1.50},
}


# --- Provedores: cada função recebe o prompt e devolve o texto da resposta ----

def chamar_aws(prompt: str) -> str:
    import boto3

    cli = boto3.client("bedrock-runtime",
                       region_name=os.getenv("AWS_DEFAULT_REGION", "us-west-2"))
    corpo = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 600, "temperature": 0.3,
        "messages": [{"role": "user", "content": prompt}],
    }
    resp = cli.invoke_model(
        modelId="anthropic.claude-3-haiku-20240307-v1:0", body=json.dumps(corpo))
    return json.loads(resp["body"].read())["content"][0]["text"]


def chamar_gcp(prompt: str) -> str:
    import vertexai
    from vertexai.generative_models import GenerativeModel

    vertexai.init(project=os.getenv("GOOGLE_CLOUD_PROJECT"),
                  location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"))
    return GenerativeModel("gemini-1.5-flash").generate_content(prompt).text


def chamar_oci(prompt: str) -> str:
    from oci_common import chat
    return chat(prompt)["texto"]


PROVEDORES = {
    "AWS Bedrock (Claude 3 Haiku)": chamar_aws,
    "GCP Vertex (Gemini 1.5 Flash)": chamar_gcp,
    "OCI GenAI (Cohere Command R+)": chamar_oci,
}


def _custo_1k(nome: str, tokens_medios: int) -> float:
    """Estima US$ por 1.000 consultas assumindo ~50/50 entrada/saída."""
    p = PRECOS[nome]
    preco_por_token = (p["in"] + p["out"]) / 2 / 1_000_000
    return round(tokens_medios * preco_por_token * 1000, 4)


def avaliar(prompts: list[str]) -> dict:
    """Executa todos os prompts em cada provedor disponível e agrega métricas."""
    agregado: dict[str, dict] = {}
    for nome, fn in PROVEDORES.items():
        latencias, qualidades, tokens = [], [], []
        disponivel = True
        motivo = ""
        for idx, prompt in enumerate(prompts):
            try:
                inicio = time.perf_counter()
                texto = fn(prompt)
                latencias.append(time.perf_counter() - inicio)
                qualidades.append(nota_qualidade(texto, idx))
                tokens.append(contar_tokens(texto))
            except Exception as exc:
                disponivel = False
                motivo = str(exc)[:80]
                break

        if disponivel and latencias:
            tok_medio = sum(tokens) // len(tokens)
            agregado[nome] = {
                "disponivel": True,
                "latencia_media_s": round(sum(latencias) / len(latencias), 3),
                "qualidade_media": round(sum(qualidades) / len(qualidades), 2),
                "tokens_medios": tok_medio,
                "custo_1k_usd": _custo_1k(nome, tok_medio),
            }
        else:
            agregado[nome] = {"disponivel": False, "motivo": motivo or "sem credenciais"}
        print(f"  {nome}: {'OK' if disponivel else 'indisponível'}")
    return agregado


def gerar_markdown(agregado: dict, prompts: list[str]) -> str:
    linhas = [
        "# Comparação de IA Gerenciada — AWS x GCP x OCI",
        "",
        f"Prompts avaliados: **{len(prompts)}** (temática de infraestrutura).",
        "",
        "| Nuvem | Modelo | Latência média (s) | Qualidade (1-5) | "
        "Tokens médios | Custo / 1.000 consultas (US$) |",
        "|---|---|---|---|---|---|",
    ]
    for nome, d in agregado.items():
        if d.get("disponivel"):
            linhas.append(
                f"| {nome.split('(')[0].strip()} | {nome.split('(')[1].rstrip(')')} "
                f"| {d['latencia_media_s']} | {d['qualidade_media']} "
                f"| {d['tokens_medios']} | {d['custo_1k_usd']} |"
            )
        else:
            linhas.append(
                f"| {nome.split('(')[0].strip()} | {nome.split('(')[1].rstrip(')')} "
                f"| — | — | — | indisponível ({d.get('motivo','')}) |"
            )
    linhas += [
        "",
        "> Custo estimado pelos preços públicos por 1M de tokens, assumindo "
        "distribuição ~50/50 entre tokens de entrada e saída.",
        "> OCI GenAI é **US$ 0,00** dentro dos limites Always Free / créditos.",
    ]
    return "\n".join(linhas)


def main() -> None:
    parser = argparse.ArgumentParser(description="Comparação 3 nuvens de IA")
    parser.add_argument("prompt", nargs="?",
                        help="prompt único; sem ele, usa os 5 prompts padrão")
    args = parser.parse_args()

    prompts = [args.prompt] if args.prompt else PROMPTS_PADRAO
    print("Avaliando provedores...")
    agregado = avaliar(prompts)

    REPORTS.mkdir(exist_ok=True)
    md = gerar_markdown(agregado, prompts)
    destino = REPORTS / "three_clouds_ai_comparison.md"
    destino.write_text(md, encoding="utf-8")
    print(f"\n{md}\n\nRelatório salvo em {destino}")


if __name__ == "__main__":
    main()
