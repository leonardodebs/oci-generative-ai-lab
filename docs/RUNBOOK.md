# Runbook Operacional — OCI Generative AI Lab

Procedimentos operacionais e troubleshooting do laboratório. Cada problema traz
**sintoma → causa provável → solução**.

---

## 1. Procedimentos operacionais

### 1.1 Preparar o ambiente (primeira vez)

```bash
# Ambiente Python isolado
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Credenciais OCI (cria ~/.oci/config + par de chaves)
oci setup config
# Faça upload da chave pública em: Console OCI → Profile → API Keys

# Variáveis do projeto
cp .env.example .env          # preencha OCI_COMPARTMENT_ID

# Validação
make check                    # esperado: "OCI Generative AI: OK"
```

### 1.2 Operações do dia a dia

| Ação | Comando |
|---|---|
| Verificar ambiente | `make check` |
| Chat único | `make chat Q="..."` |
| Chat interativo | `make interactive` |
| Rodar 5 prompts padrão | `make prompts` |
| Consulta RAG | `make rag Q="..."` |
| Comparar OCI x AWS | `make compare-aws` |
| Comparar 3 nuvens | `make compare-3` |
| Subir app web | `make serve` → http://127.0.0.1:5000 |
| Rodar testes | `make test` |
| Limpar caches/índice | `make clean` |

### 1.3 Reconstruir o índice do RAG

Após alterar/adicionar runbooks em `data/runbooks/`:

```bash
python3 src/oci_rag.py --rebuild "qualquer pergunta"
# ou apague o cache e deixe reconstruir na próxima execução:
make clean
```

### 1.4 Deploy da OCI Function

Ver passo a passo em [../oci_functions_trigger/README.md](../oci_functions_trigger/README.md).
Resumo:

```bash
fn use context <contexto-oci>
fn -v deploy --app genai-app
fn config function genai-app genai-trigger OCI_COMPARTMENT_ID <ocid>
echo '{"texto":"ALB 502 em produção"}' | fn invoke genai-app genai-trigger
```

---

## 2. Troubleshooting

### 2.1 `make check` falha

**Sintoma:** `OCI Generative AI: ERRO — arquivo ~/.oci/config não encontrado`
- **Causa:** OCI CLI nunca configurado.
- **Solução:** `oci setup config` e upload da chave pública no Console.

**Sintoma:** `campos obrigatórios ausentes no config: ...`
- **Causa:** perfil incompleto (faltam `user`, `fingerprint`, `tenancy`, etc.).
- **Solução:** edite `~/.oci/config` ou rode `oci setup config` de novo.

**Sintoma:** `chave privada não encontrada: ...`
- **Causa:** `key_file` aponta para um caminho inexistente.
- **Solução:** corrija o caminho em `~/.oci/config` (use caminho absoluto).

**Sintoma:** `OCI_COMPARTMENT_ID não definido`
- **Causa:** `.env` não criado ou variável vazia.
- **Solução:** `cp .env.example .env` e preencha o OCID do compartimento.

### 2.2 Erros nas chamadas ao Generative AI

**Sintoma:** `NotAuthorizedOrNotFound` / `404`
- **Causa 1:** Generative AI não disponível na região do perfil.
- **Solução:** use uma região suportada (ex.: `us-chicago-1`, `eu-frankfurt-1`,
  `sa-saopaulo-1`); ajuste `region` no `~/.oci/config`.
- **Causa 2:** falta de *policy* IAM.
- **Solução:** crie
  `Allow group <grupo> to use generative-ai-family in compartment <nome>`.

**Sintoma:** `404` / `ModelNotFound` em um modelo específico
- **Causa:** o `model_id` não existe na região, ou nome desatualizado.
- **Solução:** liste os modelos disponíveis e ajuste `OCI_CHAT_MODEL`
  (ex.: `cohere.command-r-plus`, `meta.llama-3-70b-instruct`).

**Sintoma:** `429 TooManyRequests`
- **Causa:** limite de throughput on-demand atingido.
- **Solução:** reduza a cadência; para carga constante, considere um
  *dedicated AI cluster*.

**Sintoma:** `AttributeError` ao extrair o texto da resposta
- **Causa:** o SDK mudou a estrutura da resposta (Cohere x Generic).
- **Solução:** confira `_extrair_texto()` em
  [../src/oci_common.py](../src/oci_common.py) contra a versão atual do SDK.

### 2.3 RAG

**Sintoma:** `Nenhum runbook encontrado em data/runbooks`
- **Causa:** pasta vazia.
- **Solução:** confirme os `.md` em `data/runbooks/`.

**Sintoma:** respostas ignoram documentos novos.
- **Causa:** índice em cache desatualizado.
- **Solução:** `python3 src/oci_rag.py --rebuild "..."` ou `make clean`.

**Sintoma:** `ModuleNotFoundError: faiss`
- **Causa:** dependência não instalada.
- **Solução:** `pip install faiss-cpu`.

### 2.4 App web (Flask)

**Sintoma:** front carrega mas health fica vermelho ("Configuração incompleta").
- **Causa:** falta `~/.oci/config` e/ou `OCI_COMPARTMENT_ID`.
- **Solução:** seção 1.1.

**Sintoma:** "Backend offline — rode `make serve`".
- **Causa:** servidor não está no ar.
- **Solução:** `make serve` e recarregue a página.

**Sintoma:** `Address already in use` ao subir.
- **Causa:** porta 5000 ocupada.
- **Solução:** `PORT=5055 python3 src/server.py`.

**Sintoma:** resposta do chat vem em vermelho com "falha na inferência".
- **Causa:** problema de auth/policy/modelo (ver 2.2); o erro real está na bolha.
- **Solução:** rode `make check` e siga a seção 2.1/2.2.

### 2.5 Comparações multicloud

**Sintoma:** coluna AWS ou GCP marcada como "indisponível".
- **Causa:** credenciais/libs ausentes (`boto3`, `vertexai`) — comportamento
  esperado e tolerado por design.
- **Solução:** configure as credenciais da nuvem desejada, ou rode com
  `--no-aws` para focar no OCI.

### 2.6 Testes

**Sintoma:** testes do backend são pulados (`skipped`).
- **Causa:** Flask não instalado.
- **Solução:** `pip install flask` (ou `-r requirements.txt`).

**Sintoma:** `externally-managed-environment` ao instalar libs.
- **Causa:** Python gerenciado pelo SO (PEP 668).
- **Solução:** use `python3 -m venv .venv` (recomendado) ou, por sua conta e
  risco, `pip install --break-system-packages`.

---

## 3. Verificação de saúde (checklist)

```bash
make check        # 1. ambiente OCI OK?
make test         # 2. 19 testes passam?
make chat Q="ping"# 3. chamada real responde?
make serve        # 4. app web sobe e health fica verde?
```

Se os quatro passam, o lab está operacional.

---

## 4. Custo e contenção

- Generative AI é **on-demand**: monitore o uso no Console (Billing → Cost
  Analysis). Para custo zero, mantenha-se nos créditos iniciais.
- Em caso de pico inesperado, **revogue a API Key** no Console (Profile → API
  Keys) para cortar o acesso imediatamente.
- Functions/Compute ARM/Autonomous DB são Always Free permanentes — sem risco
  de cobrança dentro dos limites.
