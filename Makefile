# Makefile — OCI Generative AI Lab
# Uso: make <alvo>. Variáveis: Q="sua pergunta".

PY := python
SRC := src

.PHONY: help install check chat rag interactive compare-aws compare-3 prompts serve test clean

help:  ## Lista os alvos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n",$$1,$$2}'

install:  ## Instala as dependências
	pip install -r requirements.txt

check:  ## Verifica a configuração do ambiente OCI
	$(PY) $(SRC)/setup_check.py

chat:  ## Chat único — make chat Q="Explique NAT vs Internet Gateway"
	$(PY) $(SRC)/oci_chat.py "$(Q)"

interactive:  ## Chat em modo loop interativo
	$(PY) $(SRC)/oci_chat.py --interactive

prompts:  ## Roda os 5 prompts padrão de infraestrutura
	$(PY) $(SRC)/oci_chat.py --prompts

rag:  ## RAG sobre os runbooks — make rag Q="Como fazer failover do RDS?"
	$(PY) $(SRC)/oci_rag.py "$(Q)"

compare-aws:  ## Comparação OCI x AWS Bedrock
	$(PY) $(SRC)/oci_vs_aws_comparison.py

compare-3:  ## Comparação final 3 nuvens (AWS x GCP x OCI)
	$(PY) $(SRC)/three_clouds_comparison.py

serve:  ## Sobe o mini-app de chat em http://127.0.0.1:5000
	$(PY) $(SRC)/server.py

test:  ## Roda a suíte de testes
	pytest -q

clean:  ## Remove caches e índice gerado
	rm -rf $(SRC)/__pycache__ tests/__pycache__ .pytest_cache data/faiss_index.pkl
