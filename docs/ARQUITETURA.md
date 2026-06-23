# Documentação de Arquitetura — OCI Generative AI Lab

Detalhes técnicos da arquitetura do laboratório: componentes, fluxos de dados,
decisões de design e os limites de segurança.

---

## 1. Visão geral

O projeto demonstra IA generativa gerenciada na Oracle Cloud (OCI) em quatro
frentes, todas apoiadas no mesmo SDK e nas mesmas credenciais:

```
                         ┌────────────────────────────────────────┐
                         │            OCI Generative AI            │
                         │   GenerativeAiInferenceClient (SDK)     │
                         │   ┌──────────────┐  ┌────────────────┐  │
                         │   │  chat()      │  │  embed_text()  │  │
                         │   │ Cohere/Llama │  │  Cohere Embed  │  │
                         │   └──────────────┘  └────────────────┘  │
                         └───────▲───────────────▲────────────────┘
                                 │               │
        ┌────────────────────────┼───────────────┼─────────────────────┐
        │                        │               │                     │
  ┌─────┴──────┐       ┌─────────┴────┐   ┌──────┴───────┐    ┌────────┴────────┐
  │  CLI       │       │  Web app     │   │  RAG         │    │  OCI Function   │
  │ oci_chat   │       │ server.py +  │   │ oci_rag +    │    │ func.py         │
  │ + compare  │       │ web/ (Flask) │   │ FAISS local  │    │ (Resource Princ)│
  └────────────┘       └──────────────┘   └──────────────┘    └─────────────────┘
```

Camada compartilhada: **[src/oci_common.py](../src/oci_common.py)** centraliza a
criação do client, `chat()` e `embed()`, evitando duplicação entre os módulos.

---

## 2. Componentes

| Componente | Arquivo | Responsabilidade |
|---|---|---|
| **Verificação** | `src/setup_check.py` | Valida config, SDK, endpoint e compartimento |
| **Camada comum** | `src/oci_common.py` | Client memoizado, `chat()` (Cohere/Llama), `embed()` |
| **Chat CLI** | `src/oci_chat.py` | Prompt único, modo interativo, 5 prompts padrão |
| **RAG** | `src/oci_rag.py` | Chunking → embeddings OCI → FAISS → geração fundamentada |
| **Comparações** | `src/oci_vs_aws_comparison.py`, `src/three_clouds_comparison.py` | Métricas lado a lado (latência, tokens, qualidade, custo) |
| **Qualidade** | `src/quality.py` | Heurística 1-5 por cobertura de palavras-chave |
| **Backend web** | `src/server.py` | Flask: serve o front e expõe `/api/chat`, `/api/rag`, `/api/health` |
| **Front-end** | `web/` | Chat + RAG; fala somente com o backend local |
| **Function** | `oci_functions_trigger/` | Função serverless (Fn) que chama o GenAI por Resource Principal |

---

## 3. Fluxos de dados

### 3.1 Chat (CLI ou Web)

```
usuário → oci_chat / web → oci_common.chat()
        → GenerativeAiInferenceClient.chat(ChatDetails)
        → OCI Generative AI (OnDemandServingMode: model_id)
        → resposta normalizada {texto, modelo}
```

`chat()` decide a estrutura do request pelo prefixo do modelo:
- `cohere.*` → `CohereChatRequest` (campo `message`, resposta em `.text`)
- demais (`meta.llama*`) → `GenericChatRequest` (`messages[]`, resposta em
  `choices[0].message.content[0].text`)

### 3.2 RAG (Retrieval-Augmented Generation)

```
indexação (1x):
  data/runbooks/*.md → chunks (800 chars) → embed() [Cohere Embed v3]
  → numpy float32 → faiss.normalize_L2 → IndexFlatIP → cache em disco

consulta:
  pergunta → embed() → busca top-4 (produto interno = cosseno)
  → monta prompt com contexto + pergunta → chat() → resposta fundamentada
```

Decisão: **FAISS local** (não Oracle DB 23ai) para manter custo zero e
portabilidade. Em produção enterprise, o caminho natural seria **AI Vector
Search no Autonomous Database 23ai** (RAG sem mover dados).

### 3.3 OCI Function

```
evento JSON {texto} → handler → Resource Principal signer
  → GenerativeAiInferenceClient → triagem SRE → resposta JSON {analise}
```

---

## 4. Modelo de autenticação

| Contexto | Método | Por quê |
|---|---|---|
| CLI / RAG / Web (local) | **API Key** (`~/.oci/config`) | Padrão para dev/estação de trabalho |
| OCI Function | **Resource Principal** | Serverless não tem config local; a identidade vem da Dynamic Group |
| Comparações AWS/GCP | IAM Role / Service Account | Credenciais nativas de cada nuvem |

**Limite de segurança crítico:** no app web, as credenciais OCI vivem **apenas
no backend** (`server.py`). O navegador chama só `/api/*`; nenhum segredo é
exposto ao client. O `/api/health` reporta status sem revelar valores.

---

## 5. Endpoints da API (backend Flask)

| Método | Rota | Corpo | Resposta |
|---|---|---|---|
| GET | `/` | — | `web/index.html` |
| GET | `/<arquivo>` | — | estáticos de `web/` |
| GET | `/api/health` | — | `{pronto, config_oci, compartment_id, modelo_padrao}` |
| POST | `/api/chat` | `{prompt, model?}` | `{texto, modelo, latencia_s}` |
| POST | `/api/rag` | `{pergunta}` | `{texto, latencia_s}` |

Erros retornam `{erro: "..."}` com status 400 (validação) ou 500 (inferência).

---

## 6. Decisões de design

| Decisão | Alternativa | Justificativa |
|---|---|---|
| Camada `oci_common` única | Código repetido por script | DRY; um só ponto para client/auth |
| Import tardio do SDK (`import oci` dentro das funções) | Import no topo | Permite testes com fake SDK e mensagens de erro claras se faltar a lib |
| FAISS local | Oracle DB 23ai / Vector Search | Custo zero, sem dependência de banco |
| Fallback "indisponível" nas comparações | Falhar tudo | Relatório sai com as nuvens presentes |
| Backend Flask para o front | Chamar OCI do browser | Segurança: segredo não vai ao client |
| Heurística de qualidade (palavras-chave) | LLM-as-judge | Reprodutível, barato, sem custo extra |

---

## 7. Estratégia de testes

Os testes rodam **sem credenciais nem rede** (ver `tests/conftest.py`):
- **Fake do SDK `oci`** injetado em `sys.modules` cobre `chat()`/`embed()`.
- **Fake do `faiss`** (cosseno via numpy) cobre o pipeline de RAG.
- **Test client do Flask** cobre as rotas do backend.

O único caminho não coberto por testes é o **handshake real** com o endpoint
OCI — validado manualmente via `make check` / `make chat` contra a conta.

---

## 8. Custo e limites

- Generative AI é **on-demand** (cobrado por token fora dos créditos iniciais
  de US$ 300 / 30 dias). Uso de portfólio fica em **US$ 0,00**.
- OCI Functions: **2.000.000 invocações/mês** Always Free (permanente).
- Compute ARM, Object Storage e Autonomous DB 23ai: Always Free permanente.

Ver detalhes em [../README.md](../README.md) e procedimentos em
[RUNBOOK.md](RUNBOOK.md).
