const form = document.getElementById("cadastroForm");
const senhaInput = document.getElementById("senha");
const confirmarInput = document.getElementById("confirmar_senha");
const senhaErro = document.getElementById("senhaErro");
const confirmarErro = document.getElementById("confirmarErro");

function validarSenha() {
    let valido = true;
    const senha = senhaInput.value;
    const regexForca = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/;

    if (senha.length > 0 && !regexForca.test(senha)) {
        senhaErro.textContent = "A senha precisa ter no mínimo 8 caracteres, incluindo maiúscula, minúscula, número e caractere especial.";
        senhaErro.classList.add("active");
        senhaInput.classList.add("invalid");
        valido = false;
    } else {
        senhaErro.textContent = "A senha deve ter no mínimo 8 caracteres.";
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