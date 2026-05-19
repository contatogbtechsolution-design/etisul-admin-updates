document.querySelectorAll("[data-share-url]").forEach((button) => {
    button.addEventListener("click", async () => {
        const url = button.dataset.shareUrl;
        const title = button.dataset.shareTitle || "Produto Etisul";
        if (navigator.share) {
            await navigator.share({ title, url });
            return;
        }
        await navigator.clipboard.writeText(url);
        const textoOriginal = button.textContent;
        button.textContent = "Link copiado";
        window.setTimeout(() => {
            button.textContent = textoOriginal;
        }, 1600);
    });
});
