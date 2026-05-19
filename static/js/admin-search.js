(function () {
    const inputs = document.querySelectorAll("[data-live-search]");

    inputs.forEach((input) => {
        const targetSelector = input.getAttribute("data-live-search");
        const rows = Array.from(document.querySelectorAll(targetSelector));

        input.addEventListener("input", () => {
            const term = input.value.trim().toLowerCase();

            rows.forEach((row) => {
                const text = (row.getAttribute("data-search") || row.textContent || "").toLowerCase();
                row.hidden = term && !text.includes(term);
            });
        });
    });
})();
