# OCI Generative AI Lab

[![CI](https://github.com/leonardodebs/oci-generative-ai-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/leonardodebs/oci-generative-ai-lab/actions/workflows/ci.yml)
![Oracle Cloud](https://img.shields.io/badge/Oracle_Cloud-F80000?style=flat&logo=oracle&logoColor=white)
![Cohere](https://img.shields.io/badge/Cohere_Command_R+-39594D?style=flat&logo=cohere&logoColor=white)
![Llama](https://img.shields.io/badge/Meta_Llama_3-0467DF?style=flat&logo=meta&logoColor=white)
![AWS](https://img.shields.io/badge/AWS_Bedrock-FF9900?style=flat&logo=amazonwebservices&logoColor=white)
![GCP](https://img.shields.io/badge/Google_Cloud-4285F4?style=flat&logo=googlecloud&logoColor=white)
![Python](https://img.shields.io/badge/Python_3.12-3776AB?style=flat&logo=python&logoColor=white)
![Always Free](https://img.shields.io/badge/Custo-US$_0.00-3fb950?style=flat)

Projeto de portfólio que demonstra as capacidades de IA generativa da **Oracle
Cloud Infrastructure (OCI)** — chat, embeddings, RAG e Functions serverless —
e as compara lado a lado com **AWS Bedrock** e **GCP Vertex AI**.

> **Contexto:** já uso OCI no trabalho (Wareline). Este lab estende esse
> conhecimento para a área de IA generativa. Tudo roda no **OCI Always Free
> Tier** — **custo: US$ 0,00**.

Faz parte da série multicloud:
[`aws-bedrock`](../../) · [`gcp-vertex-ai`](../gcp-vertex-ai) ·
[`azure-openai`](../azure-openai) · **`oci-generative-ai`** (este).

---

## Estrutura

```
oci-generative-ai/
├── src/
│   ├── setup_check.py            # valida ambiente OCI (config, SDK, endpoint)
│   ├── oci_common.py             # helpers compartilhados (client, chat, embed)
│   ├── oci_chat.py               # chat com Cohere Command R+ / Llama 3 70B
│   ├── oci_vs_aws_comparison.py  # OCI x AWS Bedrock
│   ├── oci_rag.py                # RAG com OCI Embeddings + FAISS
│   ├── three_clouds_comparison.py# AWS x GCP x OCI
│   └── quality.py                # heurística de qualidade (1-5)
│   └── server.py                 # backend Flask do mini-app de chat
├── web/                          # front-end (chat + RAG) — fala só com o backend
│   ├── index.html · style.css · app.js
├── oci_functions_trigger/        # OCI Function (Fn Project) que chama o GenAI
│   ├── func.py · func.yaml · requirements.txt · README.md
├── data/runbooks/                # runbooks reutilizados (base do RAG)
├── reports/                      # relatórios gerados
├── tests/                        # testes das funções puras (sem nuvem)
├── requirements.txt · .env.example · Makefile · README.md
```

---

## Setup — OCI CLI + SDK

1. **Instalar o OCI CLI** e configurar a autenticação por API Key:
   ```bash
   bash -c "$(curl -L https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh)"
   oci setup config        # cria ~/.oci/config + par de chaves
   ```
   Faça o upload da chave pública gerada em **Console OCI → Profile → API Keys**.

2. **Habilitar o Generative AI** na sua região (disponível em regiões como
   `us-chicago-1`, `eu-frankfurt-1`, `sa-saopaulo-1`). Crie a *policy*:
   ```
   Allow group <seu-grupo> to use generative-ai-family in compartment <nome>
   ```

3. **Instalar dependências e configurar o `.env`:**
   ```bash
   make install
   cp .env.example .env     # preencha OCI_COMPARTMENT_ID
   make check               # deve imprimir "OCI Generative AI: OK"
   ```

---

## Uso

```bash
make check                                   # valida o ambiente
make chat Q="Explique NAT Gateway vs Internet Gateway"
make interactive                             # modo loop
make prompts                                 # 5 prompts padrão de infra
make rag Q="Como fazer failover do RDS?"     # RAG sobre os runbooks
make compare-aws                             # OCI x AWS Bedrock
make compare-3                               # AWS x GCP x OCI
make serve                                   # mini-app de chat em http://127.0.0.1:5000
make test                                    # testes locais (sem nuvem)
```

### Mini-app de chat (web/)

Front-end leve (HTML/CSS/JS puro) com dois modos — **Chat** e **RAG** sobre os
runbooks — servido pelo backend Flask em [src/server.py](src/server.py).

> **Segurança:** as credenciais OCI ficam **só no backend**. O navegador chama
> apenas `/api/chat` e `/api/rag` no servidor local; nada de segredo no client.

```bash
make serve            # sobe Flask em http://127.0.0.1:5000
```

Endpoints: `GET /api/health` (status do ambiente, sem expor segredos),
`POST /api/chat` (`{prompt, model}`), `POST /api/rag` (`{pergunta}`).

Modelos usáveis (`--model` no `oci_chat.py` ou `OCI_CHAT_MODEL` no `.env`):
`cohere.command-r-plus` (padrão) ou `meta.llama-3-70b-instruct`.

---

## OCI vs AWS vs GCP — serviços de IA

| Recurso | **OCI Generative AI** | **AWS** | **GCP** |
|---|---|---|---|
| Serviço gerenciado | Generative AI Inference | Bedrock | Vertex AI |
| Modelos de chat | Cohere Command R/R+, Meta Llama 3 | Claude, Llama, Titan, Mistral | Gemini 1.5 Pro/Flash |
| Embeddings | Cohere Embed v3 (multilíngue) | Titan Embeddings, Cohere | text-embedding-004 |
| SDK Python | `oci.generative_ai_inference` | `boto3` (`bedrock-runtime`) | `google-cloud-aiplatform` |
| Auth serverless | Resource Principal (Functions) | IAM Role | Service Account / Workload Identity |
| Serverless trigger | OCI Functions (Fn Project) | Lambda | Cloud Functions |
| Vector store gerenciado | Oracle DB 23ai (AI Vector Search) | OpenSearch / Kendra | Vertex AI Vector Search |
| Fine-tuning | T-Few / LoRA dedicado | Bedrock Custom Models | Vertex AI Tuning |

---

## OCI Always Free — o que é gratuito

| Serviço | Limite Always Free |
|---|---|
| **OCI Functions** | 2.000.000 de invocações/mês |
| **Compute (ARM Ampere A1)** | 4 OCPUs + 24 GB RAM sempre gratuitos |
| **Object Storage** | 20 GB |
| **Autonomous Database (23ai)** | 2 instâncias (inclui AI Vector Search) |
| **Generative AI** | Coberto pelos **créditos iniciais de US$ 300 / 30 dias** e pelo uso dentro dos limites de teste; uso moderado de portfólio fica em **US$ 0,00** |
| **Monitoring / Logging** | Incluídos |

> **Atenção:** o Generative AI da OCI é *on-demand* (cobrado por token fora do
> período de créditos). Para custo permanentemente zero, use-o dentro dos
> créditos iniciais ou limite o volume. Compute ARM, Functions e Autonomous DB
> são **Always Free de verdade** (sem expirar).

---

## Quando o OCI GenAI tem vantagem

- **Clientes Oracle / enterprise:** integração nativa com Autonomous Database
  23ai (AI Vector Search no próprio banco — RAG sem mover dados) e com o
  ecossistema OCI já contratado (rede, IAM, observabilidade).
- **Escala de GPU a custo competitivo:** clusters de GPU dedicados (RDMA) com
  preço frequentemente abaixo dos hyperscalers para treino/inferência pesada.
- **Soberania e residência de dados:** regiões dedicadas e *dedicated AI
  clusters* para isolamento total.
- **Custo previsível:** *dedicated AI clusters* dão throughput fixo sem
  surpresa de cobrança por token em cargas constantes.
- **Always Free robusto:** Compute ARM + Functions + Autonomous DB gratuitos
  permanentemente — ótimo para protótipos e laboratórios.

AWS/GCP ainda lideram em **variedade de modelos** (Claude no Bedrock, Gemini no
Vertex) e maturidade de tooling. Este lab mostra como escolher por caso de uso.

---

## Skills demonstradas

- **OCI SDK** — `oci.config`, autenticação por API Key e Resource Principal
- **OCI Generative AI** — chat (Cohere/Llama), embeddings, serving on-demand
- **Multicloud** — mesma carga em OCI, AWS Bedrock e GCP Vertex AI, com métricas
- **RAG** — embeddings OCI + FAISS local + geração fundamentada em runbooks
- **OCI Functions** — função serverless (Fn Project) que chama o GenAI
- **Full-stack** — backend Flask + front-end de chat/RAG (segredos só no servidor)
- **Engenharia de comparação** — latência, tokens, qualidade e custo/1k queries

---

## Documentação

- [docs/ARQUITETURA.md](docs/ARQUITETURA.md) — detalhes técnicos da arquitetura
- [docs/RUNBOOK.md](docs/RUNBOOK.md) — procedimentos operacionais e troubleshooting
- [docs/VARIAVEIS-DE-AMBIENTE.md](docs/VARIAVEIS-DE-AMBIENTE.md) — template de configuração

## Custo

**US$ 0,00** — projetado para o OCI Always Free Tier / créditos iniciais.
