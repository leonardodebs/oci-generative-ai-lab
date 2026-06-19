"""
setup_check.py — Verificação do ambiente OCI Generative AI.

Confere, em ordem, tudo que é necessário para os demais scripts rodarem:
    1. Existência do arquivo ~/.oci/config e dos campos obrigatórios
    2. Conexão do SDK OCI (oci.config.from_file + validate_config)
    3. Alcance do endpoint de Generative AI Inference (instancia o client)
    4. Presença do OCI_COMPARTMENT_ID (necessário para chamar os modelos)

Saída final:
    "OCI Generative AI: OK"  -> ambiente pronto
    ou uma mensagem de erro específica apontando o que corrigir.

Uso:
    python src/setup_check.py

Custo: US$ 0,00 — apenas validação local + handshake do endpoint.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Perfil do ~/.oci/config a ser usado (DEFAULT, salvo override no .env).
PERFIL = os.getenv("OCI_CONFIG_PROFILE", "DEFAULT")
CONFIG_PATH = Path.home() / ".oci" / "config"

# Campos mínimos que um config OCI precisa ter para autenticar por API Key.
CAMPOS_OBRIGATORIOS = ["user", "fingerprint", "key_file", "tenancy", "region"]


def erro(msg: str) -> None:
    """Imprime erro padronizado e encerra com código 1."""
    print(f"OCI Generative AI: ERRO — {msg}")
    sys.exit(1)


def checar_config_local() -> dict:
    """Passo 1: valida o arquivo ~/.oci/config e seus campos."""
    if not CONFIG_PATH.exists():
        erro(
            f"arquivo {CONFIG_PATH} não encontrado. "
            "Rode 'oci setup config' ou crie o config manualmente."
        )

    try:
        import oci  # import tardio para dar mensagem clara se faltar o SDK
    except ImportError:
        erro("SDK 'oci' não instalado. Rode: pip install -r requirements.txt")

    try:
        config = oci.config.from_file(file_location=str(CONFIG_PATH), profile_name=PERFIL)
    except Exception as exc:  # perfil inexistente, parse inválido, etc.
        erro(f"falha ao ler o perfil '{PERFIL}' em {CONFIG_PATH}: {exc}")

    faltando = [c for c in CAMPOS_OBRIGATORIOS if not config.get(c)]
    if faltando:
        erro(f"campos obrigatórios ausentes no config: {', '.join(faltando)}")

    # A chave privada apontada por key_file precisa existir no disco.
    key_file = Path(os.path.expanduser(config["key_file"]))
    if not key_file.exists():
        erro(f"chave privada não encontrada: {key_file}")

    print(f"[1/4] Config OCI OK (perfil '{PERFIL}', região {config['region']})")
    return config


def validar_sdk(config: dict) -> None:
    """Passo 2: valida a assinatura do config pelo próprio SDK."""
    import oci

    try:
        oci.config.validate_config(config)
    except Exception as exc:
        erro(f"validação do SDK falhou: {exc}")
    print("[2/4] Validação do SDK OCI OK")


def testar_endpoint_genai(config: dict) -> None:
    """Passo 3: instancia o client de inferência (handshake do endpoint)."""
    import oci

    regiao = config["region"]
    endpoint = f"https://inference.generativeai.{regiao}.oci.oraclecloud.com"
    try:
        oci.generative_ai_inference.GenerativeAiInferenceClient(
            config=config,
            service_endpoint=endpoint,
            retry_strategy=oci.retry.NoneRetryStrategy(),
            timeout=(10, 30),
        )
    except Exception as exc:
        erro(f"não foi possível criar o client de Generative AI: {exc}")
    print(f"[3/4] Endpoint Generative AI alcançável ({endpoint})")


def checar_compartment() -> None:
    """Passo 4: confere a variável de compartimento usada nas inferências."""
    comp = os.getenv("OCI_COMPARTMENT_ID")
    if not comp:
        erro("variável OCI_COMPARTMENT_ID não definida (veja .env.example).")
    print("[4/4] OCI_COMPARTMENT_ID definido")


def main() -> None:
    config = checar_config_local()
    validar_sdk(config)
    testar_endpoint_genai(config)
    checar_compartment()
    print("\nOCI Generative AI: OK")


if __name__ == "__main__":
    main()
