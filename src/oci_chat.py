"""
oci_chat.py — Chat com o OCI Generative AI (Cohere Command R+ ou Llama 3 70B).

Equivalente conceitual:
    AWS  -> bedrock-runtime.converse / invoke_model
    GCP  -> Vertex AI GenerativeModel.generate_content

Aqui usamos oci.generative_ai_inference.GenerativeAiInferenceClient.chat().

Uso:
    python src/oci_chat.py "Explique NAT Gateway vs Internet Gateway"
    python src/oci_chat.py --interactive          # modo loop
    python src/oci_chat.py --prompts              # roda os 5 prompts padrão
    python src/oci_chat.py --model meta.llama-3-70b-instruct "..."

Custo: US$ 0,00 dentro dos limites Always Free / créditos iniciais.
"""
from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

from oci_common import MODELO_CHAT, chat

load_dotenv()

# Os mesmos 5 prompts de infraestrutura usados no lab GCP — base de comparação.
PROMPTS_PADRAO = [
    "Explique a diferença entre NAT Gateway e Internet Gateway na AWS",
    "Quais são os 5 principais riscos de segurança em uma VPC pública?",
    "Escreva um script Python para listar instâncias EC2 paradas",
    "Compare Kubernetes e ECS para cargas de trabalho de produção",
    "Qual a diferença entre RTO e RPO em disaster recovery?",
]


def responder(prompt: str, modelo: str) -> str:
    """Chama o modelo e devolve apenas o texto da resposta."""
    return chat(prompt, modelo=modelo)["texto"]


def modo_interativo(modelo: str) -> None:
    """Loop de conversa no terminal; 'sair'/'exit'/Ctrl-D encerra."""
    print(f"Chat OCI Generative AI ({modelo}). Digite 'sair' para encerrar.\n")
    while True:
        try:
            pergunta = input("você> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if pergunta.lower() in {"sair", "exit", "quit", ""}:
            break
        print(f"\n{modelo}>\n{responder(pergunta, modelo)}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Chat com OCI Generative AI")
    parser.add_argument("pergunta", nargs="?", help="prompt único a enviar")
    parser.add_argument("--interactive", action="store_true", help="modo loop")
    parser.add_argument("--prompts", action="store_true",
                        help="executa os 5 prompts padrão de infraestrutura")
    parser.add_argument("--model", default=MODELO_CHAT,
                        help=f"modelo OCI (padrão: {MODELO_CHAT})")
    args = parser.parse_args()

    if args.interactive:
        modo_interativo(args.model)
    elif args.prompts:
        for i, p in enumerate(PROMPTS_PADRAO, 1):
            print(f"\n=== Prompt {i}/5 ===\n{p}\n---")
            print(responder(p, args.model))
    elif args.pergunta:
        print(responder(args.pergunta, args.model))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
