"""
oci_common.py — Funções compartilhadas para falar com o OCI Generative AI.

Centraliza a criação do client, a chamada de chat (Cohere/Llama) e a geração
de embeddings, para que oci_chat / oci_rag / comparações não dupliquem código.

Modelos padrão (Always Free / on-demand):
    Chat:       cohere.command-r-plus  (alternativa: meta.llama-3-70b-instruct)
    Embeddings: cohere.embed-multilingual-v3.0

Todas as funções respeitam OCI_COMPARTMENT_ID e OCI_CONFIG_PROFILE do ambiente.
"""
from __future__ import annotations

import os
from functools import lru_cache

# Modelos padrão — sobrescrevíveis por variável de ambiente.
MODELO_CHAT = os.getenv("OCI_CHAT_MODEL", "cohere.command-r-plus")
MODELO_EMBED = os.getenv("OCI_EMBED_MODEL", "cohere.embed-multilingual-v3.0")
PERFIL = os.getenv("OCI_CONFIG_PROFILE", "DEFAULT")


def _compartment_id() -> str:
    comp = os.getenv("OCI_COMPARTMENT_ID")
    if not comp:
        raise RuntimeError("OCI_COMPARTMENT_ID não definido (veja .env.example).")
    return comp


@lru_cache(maxsize=1)
def get_client():
    """Cria (e memoiza) o GenerativeAiInferenceClient para a região do perfil."""
    import oci

    config = oci.config.from_file(profile_name=PERFIL)
    regiao = config["region"]
    endpoint = f"https://inference.generativeai.{regiao}.oci.oraclecloud.com"
    return oci.generative_ai_inference.GenerativeAiInferenceClient(
        config=config,
        service_endpoint=endpoint,
        retry_strategy=oci.retry.NoneRetryStrategy(),
        timeout=(10, 240),
    ), config


def _serving_mode(modelo: str):
    """OnDemandServingMode aponta a inferência para o model_id informado."""
    import oci

    return oci.generative_ai_inference.models.OnDemandServingMode(model_id=modelo)


def chat(prompt: str, modelo: str | None = None, max_tokens: int = 600,
         temperatura: float = 0.3) -> dict:
    """
    Envia um prompt de chat e devolve dict com texto e contagem de tokens.

    Suporta tanto a família Cohere quanto a família Llama (Meta), que usam
    estruturas de request diferentes no SDK de inferência da OCI.
    """
    import oci
    from oci.generative_ai_inference import models as m

    modelo = modelo or MODELO_CHAT
    client, _ = get_client()

    if modelo.startswith("cohere"):
        chat_req = m.CohereChatRequest(
            message=prompt,
            max_tokens=max_tokens,
            temperature=temperatura,
        )
    else:  # família Llama / genérica
        conteudo = m.TextContent(text=prompt)
        mensagem = m.Message(role="USER", content=[conteudo])
        chat_req = m.GenericChatRequest(
            messages=[mensagem],
            api_format=m.BaseChatRequest.API_FORMAT_GENERIC,
            max_tokens=max_tokens,
            temperature=temperatura,
        )

    detalhes = m.ChatDetails(
        serving_mode=_serving_mode(modelo),
        compartment_id=_compartment_id(),
        chat_request=chat_req,
    )

    resp = client.chat(detalhes)
    return _extrair_texto(resp, modelo)


def _extrair_texto(resp, modelo: str) -> dict:
    """Normaliza a resposta do SDK (Cohere x Generic) em texto + uso."""
    data = resp.data.chat_response
    if modelo.startswith("cohere"):
        texto = data.text
    else:
        # GenericChatResponse: choices[0].message.content[0].text
        texto = data.choices[0].message.content[0].text

    return {"texto": texto, "modelo": modelo}


def embed(textos: list[str], modelo: str | None = None) -> list[list[float]]:
    """Gera embeddings para uma lista de textos (máx. 96 por chamada na OCI)."""
    from oci.generative_ai_inference import models as m

    modelo = modelo or MODELO_EMBED
    client, _ = get_client()

    vetores: list[list[float]] = []
    for i in range(0, len(textos), 96):
        lote = textos[i:i + 96]
        detalhes = m.EmbedTextDetails(
            serving_mode=_serving_mode(modelo),
            compartment_id=_compartment_id(),
            inputs=lote,
            truncate="END",
        )
        resp = client.embed_text(detalhes)
        vetores.extend(resp.data.embeddings)
    return vetores
