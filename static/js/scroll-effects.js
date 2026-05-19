document.addEventListener("DOMContentLoaded", () => {
    const animatedSelectors = [
        "h1",
        "h2",
        "h3",
        "p",
        ".produto-card",
        ".cliente-card",
        ".info-section",
        ".carrinho-item",
        ".resumo-carrinho",
        ".container table",
        ".form-produto",
        ".produto-nao-encontrado",
        ".orcamento-intro",
        ".orcamento-card",
        ".contato-info",
        ".duvidas-form",
        ".sobre-empresa-hero",
        ".sobre-empresa-card",
        ".sobre-empresa-valores div"
    ];

    const elements = document.querySelectorAll(animatedSelectors.join(","));

    elements.forEach((element, index) => {
        if (element.closest(".loja-topo, .navbar, .menu")) {
            return;
        }

        element.classList.add("scroll-reveal");
        element.style.setProperty("--reveal-delay", `${Math.min(index * 35, 240)}ms`);
    });

    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.classList.add("scroll-reveal-visible");
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.12,
        rootMargin: "0px 0px -45px 0px"
    });

    document.querySelectorAll(".scroll-reveal").forEach((element) => {
        observer.observe(element);
    });
});
