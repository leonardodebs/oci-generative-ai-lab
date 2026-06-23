# Variáveis de Ambiente — OCI Generative AI Lab

Template e referência completa de configuração. O projeto lê as variáveis de um
arquivo `.env` (via `python-dotenv`). Comece copiando o template:

```bash
cp .env.example .env
```

> **Nunca** versione o `.env` — ele está no `.gitignore`. Versione apenas o
> `.env.example` com valores de exemplo.

---

## 1. Template completo

```dotenv
# === OCI Generative AI (obrigatório) ===
OCI_COMPARTMENT_ID=ocid1.compartment.oc1..xxxx
OCI_CONFIG_PROFILE=DEFAULT
OCI_CHAT_MODEL=cohere.command-r-plus
OCI_EMBED_MODEL=cohere.embed-multilingual-v3.0

# === Backend web (opcional) ===
PORT=5000

# === AWS Bedrock (opcional — comparação) ===
AWS_ACCESS_KEY_ID=your_key_here
AWS_SECRET_ACCESS_KEY=your_key_here
AWS_DEFAULT_REGION=us-west-2

# === GCP Vertex AI (opcional — comparação 3 nuvens) ===
GOOGLE_CLOUD_PROJECT=your_project_id
GOOGLE_CLOUD_LOCATION=us-central1

# === Anthropic direto (opcional) ===
ANTHROPIC_API_KEY=your_key_here
```

---

## 2. Referência detalhada

### 2.1 OCI Generative AI (obrigatório)

| Variável | Obrigatória | Padrão | Descrição |
|---|---|---|---|
| `OCI_COMPARTMENT_ID` | **Sim** | — | OCID do compartimento onde o GenAI é chamado. Encontre em Console → Identity → Compartments. |
| `OCI_CONFIG_PROFILE` | Não | `DEFAULT` | Nome do perfil dentro de `~/.oci/config`. Útil se você tem múltiplas tenancies. |
| `OCI_CHAT_MODEL` | Não | `cohere.command-r-plus` | Modelo de chat. Alternativa: `meta.llama-3-70b-instruct`. |
| `OCI_EMBED_MODEL` | Não | `cohere.embed-multilingual-v3.0` | Modelo de embeddings usado no RAG. |

> A **região** não é uma variável de ambiente: vem do campo `region` em
> `~/.oci/config` e define o endpoint
> `https://inference.generativeai.<região>.oci.oraclecloud.com`.

### 2.2 Backend web (opcional)

| Variável | Padrão | Descrição |
|---|---|---|
| `PORT` | `5000` | Porta do servidor Flask (`make serve`). Use outra se a 5000 estiver ocupada. |

### 2.3 AWS Bedrock — comparação (opcional)

| Variável | Padrão | Descrição |
|---|---|---|
| `AWS_ACCESS_KEY_ID` | — | Credencial AWS para `oci_vs_aws_comparison.py` e `three_clouds_comparison.py`. |
| `AWS_SECRET_ACCESS_KEY` | — | Segredo da credencial AWS. |
| `AWS_DEFAULT_REGION` | `us-west-2` | Região do Bedrock (Claude 3 Haiku). |

Sem essas variáveis, a coluna AWS aparece como **"indisponível"** (esperado).

### 2.4 GCP Vertex AI — comparação 3 nuvens (opcional)

| Variável | Padrão | Descrição |
|---|---|---|
| `GOOGLE_CLOUD_PROJECT` | — | ID do projeto GCP para o `three_clouds_comparison.py` (Gemini 1.5 Flash). |
| `GOOGLE_CLOUD_LOCATION` | `us-central1` | Região do Vertex AI. |

> A autenticação GCP usa Application Default Credentials
> (`gcloud auth application-default login`), não uma variável de ambiente.

### 2.5 Anthropic direto (opcional)

| Variável | Descrição |
|---|---|
| `ANTHROPIC_API_KEY` | Chave para uso direto da API Anthropic (fora do Bedrock), se desejado. |

---

## 3. Credenciais que NÃO ficam no `.env`

Algumas credenciais são gerenciadas pelos próprios SDKs/CLIs, não pelo `.env`:

| Recurso | Onde fica | Como configurar |
|---|---|---|
| Autenticação OCI (API Key) | `~/.oci/config` + chave privada | `oci setup config` |
| Autenticação OCI na Function | Resource Principal (Dynamic Group) | Policy IAM no Console |
| Autenticação GCP | ADC (`~/.config/gcloud/...`) | `gcloud auth application-default login` |

---

## 4. Validação

Depois de preencher o `.env`, valide tudo de uma vez:

```bash
make check
```

Saída esperada:

```
[1/4] Config OCI OK (perfil 'DEFAULT', região sa-saopaulo-1)
[2/4] Validação do SDK OCI OK
[3/4] Endpoint Generative AI alcançável (...)
[4/4] OCI_COMPARTMENT_ID definido

OCI Generative AI: OK
```

Se algo falhar, consulte a seção de troubleshooting em [RUNBOOK.md](RUNBOOK.md).
