document.querySelectorAll("[data-password-toggle]").forEach(function (button) {
    button.addEventListener("click", function () {
        const target = document.getElementById(button.dataset.passwordToggle);

        if (!target) {
            return;
        }

        const mostrarSenha = target.type === "password";
        target.type = mostrarSenha ? "text" : "password";
        button.setAttribute("aria-label", mostrarSenha ? "Ocultar senha" : "Mostrar senha");
        button.classList.toggle("senha-visivel", mostrarSenha);
    });
});
