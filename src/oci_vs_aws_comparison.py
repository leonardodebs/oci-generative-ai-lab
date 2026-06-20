"""
oci_vs_aws_comparison.py — Comparação direta OCI Generative AI x AWS Bedrock.

Para cada um dos 5 prompts de infraestrutura, roda o mesmo texto em:
    - OCI Generative AI  (cohere.command-r-plus)
    - AWS Bedrock        (anthropic.claude-3-haiku) — só se houver credenciais AWS

Mede latência (s), contagem de tokens e qualidade (1-5) e salva tudo em
reports/oci_vs_aws_comparison.json, além de imprimir uma tabela no terminal.

Design tolerante a falhas: se uma nuvem não estiver disponível, a coluna dela
fica marcada como "indisponível" e a comparação segue com a outra.

Uso:
    python src/oci_vs_aws_comparison.py
    python src/oci_vs_aws_comparison.py --no-aws
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
MODELO_BEDROCK = "anthropic.claude-3-haiku-20240307-v1:0"


def rodar_oci(prompt: str) -> dict:
    """Executa um prompt no OCI GenAI medindo latência."""
    from oci_common import chat

    inicio = time.perf_counter()
    texto = chat(prompt)["texto"]
    return _metrica("oci", texto, time.perf_counter() - inicio)


def rodar_aws(prompt: str) -> dict:
    """Executa um prompt no AWS Bedrock (Claude 3 Haiku) medindo latência."""
    import boto3

    cliente = boto3.client("bedrock-runtime",
                           region_name=os.getenv("AWS_DEFAULT_REGION", "us-west-2"))
    corpo = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 600,
        "temperature": 0.3,
        "messages": [{"role": "user", "content": prompt}],
    }
    inicio = time.perf_counter()
    resp = cliente.invoke_model(modelId=MODELO_BEDROCK, body=json.dumps(corpo))
    payload = json.loads(resp["body"].read())
    texto = payload["content"][0]["text"]
    metrica = _metrica("aws", texto, time.perf_counter() - inicio)
    # Bedrock devolve uso real de tokens — preferimos ao estimado.
    uso = payload.get("usage", {})
    if uso:
        metrica["tokens"] = uso.get("input_tokens", 0) + uso.get("output_tokens", 0)
    return metrica


def _metrica(nuvem: str, texto: str, latencia: float) -> dict:
    return {
        "nuvem": nuvem,
        "ok": True,
        "latencia_s": round(latencia, 3),
        "tokens": contar_tokens(texto),
        "resposta": texto,
    }


def _indisponivel(nuvem: str, motivo: str) -> dict:
    return {"nuvem": nuvem, "ok": False, "motivo": motivo,
            "latencia_s": None, "tokens": None, "resposta": ""}


def main() -> None:
    parser = argparse.ArgumentParser(description="OCI GenAI x AWS Bedrock")
    parser.add_argument("--no-aws", action="store_true", help="pula o Bedrock")
    args = parser.parse_args()

    resultados = []
    for idx, prompt in enumerate(PROMPTS_PADRAO):
        linha = {"prompt": prompt, "indice": idx}

        try:
            r = rodar_oci(prompt)
            r["qualidade"] = nota_qualidade(r["resposta"], idx)
            linha["oci"] = r
        except Exception as exc:
            linha["oci"] = _indisponivel("oci", str(exc))

        if args.no_aws:
            linha["aws"] = _indisponivel("aws", "desativado por --no-aws")
        else:
            try:
                r = rodar_aws(prompt)
                r["qualidade"] = nota_qualidade(r["resposta"], idx)
                linha["aws"] = r
            except Exception as exc:
                linha["aws"] = _indisponivel("aws", str(exc))

        resultados.append(linha)
        _imprimir_linha(linha)

    REPORTS.mkdir(exist_ok=True)
    destino = REPORTS / "oci_vs_aws_comparison.json"
    destino.write_text(json.dumps(resultados, indent=2, ensure_ascii=False))
    print(f"\nRelatório salvo em {destino}")


def _imprimir_linha(linha: dict) -> None:
    print(f"\n=== {linha['prompt'][:60]}... ===")
    for nuvem in ("oci", "aws"):
        d = linha[nuvem]
        if d["ok"]:
            print(f"  {nuvem.upper():4} | {d['latencia_s']:>6}s | "
                  f"{d['tokens']:>4} tok | qualidade {d['qualidade']}/5")
        else:
            print(f"  {nuvem.upper():4} | indisponível ({d['motivo'][:50]})")


if __name__ == "__main__":
    main()
