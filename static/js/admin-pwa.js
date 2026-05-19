let adminInstallPrompt = null;

if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
        navigator.serviceWorker.register("/sw-admin.js");
    });
}

window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    adminInstallPrompt = event;

    document.querySelectorAll("[data-install-admin-app]").forEach((button) => {
        button.hidden = false;
    });
});

document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-install-admin-app]");

    if (!button || !adminInstallPrompt) {
        return;
    }

    adminInstallPrompt.prompt();
    await adminInstallPrompt.userChoice;
    adminInstallPrompt = null;
    button.hidden = true;
});
