const seletorBanco = document.getElementById("banco");
const campoBusca = document.getElementById("busca");
const botaoConsultar = document.getElementById("consultar");
const mensagem = document.getElementById("mensagem");
const areaResultados = document.getElementById("resultados");

botaoConsultar.addEventListener("click", consultar);

campoBusca.addEventListener("keydown", (evento) => {
    if (evento.key === "Enter") {
        consultar();
    }
});

async function consultar() {
    const banco = seletorBanco.value;
    const busca = campoBusca.value.trim();

    if (!busca) {
        mensagem.textContent = "Digite um código ou nome de disciplina.";
        areaResultados.replaceChildren();
        return;
    }

    botaoConsultar.disabled = true;
    mensagem.textContent = "Consultando...";
    areaResultados.replaceChildren();

    try {
        const resposta = await fetch("/api/consultar", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ banco, busca })
        });

        const dados = await resposta.json();

        if (!resposta.ok) {
            throw new Error(dados.erro || "Erro na consulta.");
        }

        mensagem.textContent =
            `${dados.quantidade} resultado(s) · ${dados.tempo_ms} ms`;

        if (dados.resultados.length === 0) {
            const aviso = document.createElement("p");
            aviso.textContent = "Nenhuma disciplina encontrada.";
            areaResultados.appendChild(aviso);
            return;
        }

        dados.resultados.forEach((disciplina) => {
            const cartao = document.createElement("article");
            cartao.className = "resultado-disciplina";

            const titulo = document.createElement("h3");
            titulo.textContent =
                `${disciplina.codigo} — ${disciplina.nome}`;

            const creditos = document.createElement("p");
            creditos.textContent =
                `Créditos: ${disciplina.creditos ?? "Não informado"}`;

            const requisitos = document.createElement("p");
            const lista = disciplina.pre_requisitos || [];

            requisitos.textContent = lista.length
                ? `Pré-requisitos: ${lista.join(", ")}`
                : "Pré-requisitos: não cadastrados";

            cartao.append(titulo, creditos, requisitos);
            areaResultados.appendChild(cartao);
        });

    } catch (erro) {
        mensagem.textContent = erro.message;
    } finally {
        botaoConsultar.disabled = false;
    }
}
