"""
func.py — OCI Function (Fn Project) que chama o OCI Generative AI.

Caso de uso: receber um evento (ex.: alerta de monitoramento, log de erro) e
devolver uma análise/triagem gerada pelo OCI GenAI (Cohere Command R+).

Dentro de uma Function, autentica-se por Resource Principal (sem ~/.oci/config),
o que é o padrão recomendado para workloads serverless na OCI.

Evento de entrada esperado (JSON):
    { "texto": "ALB retornando 502 intermitente em produção", "max_tokens": 400 }

Resposta:
    { "analise": "<texto gerado>", "modelo": "cohere.command-r-plus" }
"""
import io
import json
import logging
import os

import oci
from fdk import response

MODELO = os.getenv("OCI_CHAT_MODEL", "cohere.command-r-plus")
COMPARTMENT_ID = os.getenv("OCI_COMPARTMENT_ID")


def _client():
    """Cria o client de inferência usando Resource Principal da Function."""
    signer = oci.auth.signers.get_resource_principals_signer()
    regiao = os.getenv("OCI_REGION", signer.region)
    endpoint = f"https://inference.generativeai.{regiao}.oci.oraclecloud.com"
    return oci.generative_ai_inference.GenerativeAiInferenceClient(
        config={}, signer=signer, service_endpoint=endpoint)


def _analisar(texto: str, max_tokens: int) -> str:
    """Pede ao OCI GenAI uma triagem de SRE para o texto do evento."""
    from oci.generative_ai_inference import models as m

    prompt = (
        "Você é um SRE de plantão. Analise o evento abaixo, classifique a "
        "severidade (P1-P4), liste causas prováveis e os próximos passos.\n\n"
        f"Evento: {texto}"
    )
    detalhes = m.ChatDetails(
        serving_mode=m.OnDemandServingMode(model_id=MODELO),
        compartment_id=COMPARTMENT_ID,
        chat_request=m.CohereChatRequest(
            message=prompt, max_tokens=max_tokens, temperature=0.3),
    )
    resp = _client().chat(detalhes)
    return resp.data.chat_response.text


def handler(ctx, data: io.BytesIO = None):
    """Ponto de entrada da Function (assinatura do fdk)."""
    try:
        corpo = json.loads(data.getvalue()) if data and data.getvalue() else {}
    except (ValueError, TypeError):
        corpo = {}

    texto = corpo.get("texto", "").strip()
    if not texto:
        return response.Response(
            ctx, status_code=400,
            response_data=json.dumps({"erro": "campo 'texto' é obrigatório"}),
            headers={"Content-Type": "application/json"})

    try:
        analise = _analisar(texto, int(corpo.get("max_tokens", 400)))
    except Exception as exc:  # noqa: BLE001 — devolve erro estruturado
        logging.getLogger().exception("falha na inferência")
        return response.Response(
            ctx, status_code=500,
            response_data=json.dumps({"erro": str(exc)}),
            headers={"Content-Type": "application/json"})

    return response.Response(
        ctx, status_code=200,
        response_data=json.dumps({"analise": analise, "modelo": MODELO},
                                 ensure_ascii=False),
        headers={"Content-Type": "application/json"})
