const modal = document.getElementById("modalEditar");
const formEditar = document.getElementById("formEditar");

// Função acionada pelo botão Editar na tabela HTML
function abrirModal(botao) {
    // 1. Puxa os dados escondidos no botão
    const id = botao.getAttribute("data-id");
    const nome = botao.getAttribute("data-nome");
    const email = botao.getAttribute("data-email");
    const cargo = botao.getAttribute("data-cargo");
    const admin = botao.getAttribute("data-admin");

    // 2. Preenche os campos de texto no Modal
    document.getElementById("editNome").value = nome;
    document.getElementById("editEmail").value = email;
    document.getElementById("editCargo").value = cargo;
    
    // 3. Marca a opção correta de Administrador
    if (admin === "sim") {
        document.querySelector("input[name='admin'][value='sim']").checked = true;
    } else {
        document.querySelector("input[name='admin'][value='nao']").checked = true;
    }

    // 4. Diz ao formulário para onde deve enviar os dados (Rota do Flask)
    formEditar.action = "/usuarios/editar/" + id;
    
    // 5. Exibe o modal
    modal.style.display = "block";
}

function fecharModal() {
    modal.style.display = "none";
}

// Fecha o modal ao clicar fora dele
window.addEventListener("click", (e) => {
    if (e.target === modal) {
        fecharModal();
    }
});