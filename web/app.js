// app.js — lógica do mini-app de chat OCI Generative AI.
// Fala apenas com o backend local (src/server.py); nenhuma credencial no browser.

const els = {
  mensagens: document.getElementById("mensagens"),
  form: document.getElementById("form"),
  prompt: document.getElementById("prompt"),
  enviar: document.getElementById("enviar"),
  modelo: document.getElementById("modelo"),
  configChat: document.getElementById("config-chat"),
  health: document.getElementById("health"),
  modos: document.querySelectorAll(".modo"),
};

let modo = "chat"; // "chat" | "rag"

// --- Health check do ambiente OCI -----------------------------------------
async function checarAmbiente() {
  try {
    const r = await fetch("/api/health");
    const d = await r.json();
    if (d.pronto) {
      els.health.textContent = `Ambiente OCI pronto · modelo padrão: ${d.modelo_padrao}`;
      els.health.classList.add("ok");
    } else {
      const faltam = [];
      if (!d.config_oci) faltam.push("~/.oci/config");
      if (!d.compartment_id) faltam.push("OCI_COMPARTMENT_ID");
      els.health.textContent = `Configuração incompleta: falta ${faltam.join(", ")}`;
      els.health.classList.add("bad");
    }
  } catch {
    els.health.textContent = "Backend offline — rode `make serve`";
    els.health.classList.add("bad");
  }
}

// --- Troca de modo (chat / rag) -------------------------------------------
els.modos.forEach((btn) => {
  btn.addEventListener("click", () => {
    modo = btn.dataset.modo;
    els.modos.forEach((b) => b.classList.toggle("ativo", b === btn));
    // No RAG não há escolha de modelo (usa o padrão do backend).
    els.configChat.classList.toggle("escondido", modo === "rag");
    els.prompt.placeholder = modo === "rag"
      ? "Como fazer failover do RDS?"
      : "Explique NAT Gateway vs Internet Gateway…";
  });
});

// --- Renderização de mensagens --------------------------------------------
function adicionarMsg(texto, autor, meta) {
  const div = document.createElement("div");
  div.className = `msg ${autor}`;
  const bolha = document.createElement("div");
  bolha.className = "bolha" + (autor === "erro" ? " erro" : "");
  if (autor === "erro") div.className = "msg bot";
  bolha.textContent = texto;
  div.appendChild(bolha);
  if (meta) {
    const m = document.createElement("div");
    m.className = "meta";
    m.textContent = meta;
    bolha.appendChild(m);
  }
  els.mensagens.appendChild(div);
  els.mensagens.scrollTop = els.mensagens.scrollHeight;
  return div;
}

function indicadorDigitando() {
  const div = document.createElement("div");
  div.className = "msg bot";
  div.innerHTML = '<div class="bolha"><span class="dots">'
    + '<span></span><span></span><span></span></span></div>';
  els.mensagens.appendChild(div);
  els.mensagens.scrollTop = els.mensagens.scrollHeight;
  return div;
}

// --- Envio -----------------------------------------------------------------
els.form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const texto = els.prompt.value.trim();
  if (!texto) return;

  adicionarMsg(texto, "user");
  els.prompt.value = "";
  els.enviar.disabled = true;
  const carregando = indicadorDigitando();

  try {
    const endpoint = modo === "rag" ? "/api/rag" : "/api/chat";
    const corpo = modo === "rag"
      ? { pergunta: texto }
      : { prompt: texto, model: els.modelo.value };

    const r = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corpo),
    });
    const d = await r.json();
    carregando.remove();

    if (!r.ok) {
      adicionarMsg(d.erro || "Erro desconhecido", "erro");
    } else {
      const meta = [
        d.modelo ? d.modelo : `RAG · ${els.modelo?.value || "padrão"}`,
        d.latencia_s != null ? `${d.latencia_s}s` : null,
      ].filter(Boolean).join(" · ");
      adicionarMsg(d.texto, "bot", meta);
    }
  } catch (err) {
    carregando.remove();
    adicionarMsg("Falha de rede com o backend: " + err.message, "erro");
  } finally {
    els.enviar.disabled = false;
    els.prompt.focus();
  }
});

// Enter envia; Shift+Enter quebra linha.
els.prompt.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    els.form.requestSubmit();
  }
});

checarAmbiente();
