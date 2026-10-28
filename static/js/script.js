
const banco = document.getElementById("banco");
const busca = document.getElementById("busca");
const botaoConsultar = document.getElementById("consultar");
const mensagem = document.getElementById("mensagem");
const resultados = document.getElementById("resultados");

const formCurso = document.getElementById("formCurso");
const listaDisciplinas = document.getElementById("listaDisciplinas");
const mensagemCadastro = document.getElementById("mensagemCadastro");
const resultadoCadastro = document.getElementById("resultadoCadastro");

const disciplinas = [];

function criarElemento(tag, texto) {
    const elemento = document.createElement(tag);
    elemento.textContent = texto;
    return elemento;
}

// Consulta disciplinas no banco escolhido.
botaoConsultar.addEventListener("click", async () => {
    const termo = busca.value.trim();

    mensagem.textContent = "";
    resultados.replaceChildren();

    if (!termo) {
        mensagem.textContent = "Digite o código ou nome da disciplina.";
        return;
    }

    mensagem.textContent = "Consultando...";
    botaoConsultar.disabled = true;

    try {
        const resposta = await fetch("/api/consultar", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                banco: banco.value,
                busca: termo
            })
        });

        const dados = await resposta.json();

        if (!resposta.ok) {
            mensagem.textContent = dados.erro || "Erro na consulta.";
            return;
        }

        const quantidade = dados.quantidade ?? dados.resultados.length;

        mensagem.textContent =
            `${quantidade} resultado(s), em ${dados.tempo_ms} ms.`;

        for (const disciplina of dados.resultados) {
            const card = document.createElement("article");
            card.className = "resultado";

            card.appendChild(criarElemento(
                "h3",
                `${disciplina.codigo} — ${disciplina.nome}`
            ));

            card.appendChild(criarElemento(
                "p",
                `Créditos: ${disciplina.creditos}`
            ));

            card.appendChild(criarElemento(
                "p",
                `Pré-requisitos: ${
                    (disciplina.pre_requisitos || []).join(", ") || "Nenhum"
                }`
            ));

            card.appendChild(criarElemento(
                "p",
                `Alternativos: ${
                    (disciplina.pre_requisitos_alternativos || []).join(", ")
                    || "Nenhum"
                }`
            ));

            resultados.appendChild(card);
        }
    } catch (erro) {
        mensagem.textContent = "Não foi possível comunicar com o servidor.";
    } finally {
        botaoConsultar.disabled = false;
    }
});

// Transforma os campos de pré-requisito em listas de códigos.
function separarCodigos(texto) {
    if (!texto.trim()) {
        return [];
    }

    return texto.split(",")
        .map(codigo => codigo.trim())
        .filter(Boolean);
}

// Atualiza a lista visual de disciplinas do formulário.
function atualizarLista() {
    listaDisciplinas.replaceChildren();

    for (const disciplina of disciplinas) {
        const item = document.createElement("li");

        item.appendChild(criarElemento(
            "span",
            `${disciplina.codigo} — ${disciplina.nome} (${disciplina.creditos} créditos)`
        ));

        const remover = criarElemento("button", "Remover");
        remover.type = "button";

        remover.addEventListener("click", () => {
            const indice = disciplinas.findIndex(
                d => d.codigo === disciplina.codigo
            );

            if (indice !== -1) {
                disciplinas.splice(indice, 1);
                atualizarLista();
            }
        });

        item.appendChild(remover);
        listaDisciplinas.appendChild(item);
    }
}

// Adiciona uma disciplina à lista que será enviada ao Flask.
document.getElementById("adicionarDisciplina").addEventListener("click", () => {
    const codigo = document.getElementById("codigo").value.trim();
    const nome = document.getElementById("nomeDisciplina").value.trim();
    const creditosTexto = document.getElementById("creditos").value;
    const creditos = Number(creditosTexto);

    if (!codigo || !nome || creditosTexto.trim() === "") {
        mensagemCadastro.textContent =
            "Preencha o código, o nome e os créditos da disciplina.";
        return;
    }

    if (!Number.isInteger(creditos) || creditos <= 0) {
        mensagemCadastro.textContent =
            "Os créditos precisam ser um número inteiro maior que zero.";
        return;
    }

    if (disciplinas.some(d => d.codigo === codigo)) {
        mensagemCadastro.textContent = "Esse código já está na lista.";
        return;
    }

    disciplinas.push({
        codigo,
        nome,
        creditos,
        pre_requisitos: separarCodigos(
            document.getElementById("preRequisitos").value
        ),
        pre_requisitos_alternativos: separarCodigos(
            document.getElementById("preAlternativos").value
        )
    });

    atualizarLista();
    mensagemCadastro.textContent = `${codigo} adicionada à lista.`;

    document.getElementById("codigo").value = "";
    document.getElementById("nomeDisciplina").value = "";
    document.getElementById("creditos").value = "";
    document.getElementById("preRequisitos").value = "";
    document.getElementById("preAlternativos").value = "";
});

// Envia o currículo ao Flask e mostra o resultado da sincronização.
formCurso.addEventListener("submit", async (evento) => {
    evento.preventDefault();

    mensagemCadastro.textContent = "";
    resultadoCadastro.replaceChildren();

    if (disciplinas.length === 0) {
        mensagemCadastro.textContent =
            "Adicione pelo menos uma disciplina antes de salvar.";
        return;
    }

    const dados = {
        curso: {
            nome: document.getElementById("cursoNome").value.trim(),
            instituicao: document.getElementById("instituicao").value.trim()
        },
        disciplinas: disciplinas
    };

    mensagemCadastro.textContent = "Salvando JSON e atualizando bancos...";

    const botao = formCurso.querySelector('button[type="submit"]');
    botao.disabled = true;

    try {
        const resposta = await fetch("/api/cadastrar-curso", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(dados)
        });

        const retorno = await resposta.json();

        if (!resposta.ok) {
            mensagemCadastro.textContent =
                retorno.erro || "Não foi possível salvar o currículo.";
        } else {
            mensagemCadastro.textContent =
                retorno.mensagem || "Operação concluída.";

            if (retorno.bancos) {
                const lista = document.createElement("ul");

                for (const [nomeBanco, status] of Object.entries(retorno.bancos)) {
                    lista.appendChild(criarElemento(
                        "li",
                        `${nomeBanco}: ${status}`
                    ));
                }

                resultadoCadastro.appendChild(lista);
            }

            // Limpa o formulário somente quando todos os bancos confirmarem.
            if (retorno.sucesso_total === true) {
                disciplinas.splice(0, disciplinas.length);
                atualizarLista();
                formCurso.reset();
            }
        }
    } catch (erro) {
        mensagemCadastro.textContent =
            "Erro de comunicação com o Flask.";
    } finally {
        botao.disabled = false;
    }
});
