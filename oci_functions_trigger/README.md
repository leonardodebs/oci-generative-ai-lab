# OCI Function — Gatilho de Generative AI

Function serverless (Fn Project) que recebe um evento e devolve uma triagem de
SRE gerada pelo **OCI Generative AI** (Cohere Command R+). Autentica por
**Resource Principal** — sem `~/.oci/config` dentro da Function.

## Arquivos

| Arquivo | Papel |
|---|---|
| `func.py` | Handler: recebe `{ "texto": "..." }`, chama o GenAI, retorna `{ "analise": "..." }` |
| `func.yaml` | Configuração da Function (runtime, memória, timeout) |
| `requirements.txt` | Dependências (`fdk`, `oci`) |

## Pré-requisitos

- [OCI CLI](https://docs.oracle.com/iaas/Content/API/SDKDocs/cliinstall.htm) e [Fn CLI](https://fnproject.io/) instalados
- Um **Application** de Functions criado na OCI (`fn create app ...` ou pelo Console)
- Uma **Dynamic Group** + **Policy** dando à Function acesso ao Generative AI:
  ```
  Allow dynamic-group genai-fns to use generative-ai-family in compartment <nome>
  ```

## Deploy

```bash
# 1. Apontar o contexto do Fn para o seu Application/registry da OCI
fn use context <seu-contexto-oci>

# 2. Deploy (build da imagem + push para o OCIR + criação da Function)
fn -v deploy --app genai-app

# 3. Configurar variáveis da Function
fn config function genai-app genai-trigger OCI_COMPARTMENT_ID ocid1.compartment.oc1..xxxx
fn config function genai-app genai-trigger OCI_REGION sa-saopaulo-1
```

## Invocação

```bash
echo '{"texto":"ALB retornando 502 intermitente em produção"}' \
  | fn invoke genai-app genai-trigger
```

Resposta:

```json
{ "analise": "Severidade: P2 ...", "modelo": "cohere.command-r-plus" }
```

## Custo

US$ 0,00 — OCI Functions inclui **2.000.000 de invocações/mês** no Always Free,
e o Generative AI roda dentro dos créditos/limites gratuitos.
