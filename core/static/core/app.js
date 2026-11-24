/* Funções compartilhadas pelas telas do LavaFlow */
const LF = {
    PORTE: { PEQUENO: "Pequeno", MEDIO: "Médio", GRANDE: "Grande" },
    STATUS: {
        AGUARDANDO: { rotulo: "Aguardando", cor: "#6c757d" },
        EM_ANDAMENTO: { rotulo: "Em andamento", cor: "#0d6efd" },
        FINALIZADO: { rotulo: "Finalizado", cor: "#fd7e14" },
        PAGO: { rotulo: "Pago", cor: "#198754" },
    },
    FORMAS: { DINHEIRO: "Dinheiro", PIX: "PIX", CARTAO: "Cartão" },

    /** Chama a API e devolve o JSON. Em caso de erro, lança a mensagem da API. */
    async api(metodo, url, corpo) {
        const opcoes = { method: metodo, headers: { "Content-Type": "application/json" } };
        if (corpo !== undefined) opcoes.body = JSON.stringify(corpo);
        const resp = await fetch(url, opcoes);
        const dados = await resp.json().catch(() => ({}));
        if (!resp.ok) {
            let mensagem = dados.erro || `Erro ${resp.status}`;
            if (dados.detalhes) {
                mensagem += " " + Object.entries(dados.detalhes)
                    .map(([campo, msg]) => `${campo}: ${msg}`).join(" | ");
            }
            throw new Error(mensagem);
        }
        return dados;
    },

    moeda(valor) {
        return Number(valor || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
    },

    /** Escapa texto antes de colocar em innerHTML. */
    esc(texto) {
        const div = document.createElement("div");
        div.textContent = texto ?? "";
        return div.innerHTML;
    },

    hoje() {
        const d = new Date();
        d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
        return d.toISOString().slice(0, 10);
    },

    aviso(mensagem, tipo = "success") {
        const area = document.getElementById("avisos");
        const toast = document.createElement("div");
        toast.className = `toast align-items-center text-bg-${tipo} border-0`;
        toast.setAttribute("role", "alert");
        toast.innerHTML = `<div class="d-flex"><div class="toast-body">${LF.esc(mensagem)}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div>`;
        area.appendChild(toast);
        const t = new bootstrap.Toast(toast, { delay: 5000 });
        toast.addEventListener("hidden.bs.toast", () => toast.remove());
        t.show();
    },
};
