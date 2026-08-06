const form = document.getElementById("cadastroForm");
const senhaInput = document.getElementById("senha");
const confirmarInput = document.getElementById("confirmar_senha");
const senhaErro = document.getElementById("senhaErro");
const confirmarErro = document.getElementById("confirmarErro");

function validarSenha() {
    let valido = true;

    if (senhaInput.value.length > 0 && senhaInput.value.length < 6) {
        senhaErro.classList.add("active");
        senhaInput.classList.add("invalid");
        valido = false;
    } else {
        senhaErro.classList.remove("active");
        senhaInput.classList.remove("invalid");
    }

    if (confirmarInput.value.length > 0 && confirmarInput.value !== senhaInput.value) {
        confirmarErro.classList.add("active");
        confirmarInput.classList.add("invalid");
        valido = false;
    } else {
        confirmarErro.classList.remove("active");
        confirmarInput.classList.remove("invalid");
    }

    return valido;
}

senhaInput.addEventListener("input", validarSenha);
confirmarInput.addEventListener("input", validarSenha);

const togglePasswordButtons = document.querySelectorAll(".toggle-password");
togglePasswordButtons.forEach((button) => {
    button.addEventListener("click", (event) => {
        event.preventDefault();
        const targetId = button.dataset.target;
        const input = document.getElementById(targetId);
        const icon = button.querySelector("i");
        const isPassword = input.type === "password";
        input.type = isPassword ? "text" : "password";
        icon.className = isPassword ? "fa-solid fa-eye-slash" : "fa-solid fa-eye";
        button.setAttribute("aria-label", isPassword ? "Ocultar senha" : "Mostrar senha");
    });
});

// Apenas validação visual. O HTML com enctype enviará a requisição POST para o Flask sozinho.
form.addEventListener("submit", (e) => {
    if (!validarSenha()) {
        e.preventDefault(); // Impede o envio apenas se as senhas estiverem erradas
    }
});