const { app, BrowserWindow, dialog, shell } = require("electron");
const { autoUpdater } = require("electron-updater");
const { spawn } = require("child_process");
const http = require("http");
const path = require("path");
const fs = require("fs");

const APP_NAME = "Etisul Admin";
const PORT = process.env.ETISUL_FLASK_PORT || "5000";
const ADMIN_URL = `http://127.0.0.1:${PORT}/login`;
const ADMIN_HOME_URL = `http://127.0.0.1:${PORT}/admin`;

let flaskProcess = null;
let mainWindow = null;

autoUpdater.autoDownload = true;
autoUpdater.autoInstallOnAppQuit = true;

function projectRoot() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, "etisul");
  }

  return path.resolve(__dirname, "..", "..");
}

function pythonCandidates() {
  const configured = process.env.ETISUL_PYTHON;
  const candidates = [];

  candidates.push("python", "py");
  if (configured) candidates.push(configured);
  candidates.push(path.join(process.env.LOCALAPPDATA || "", "Programs", "Python", "Python314", "python.exe"));
  candidates.push(path.join(process.env.LOCALAPPDATA || "", "Programs", "Python", "Python313", "python.exe"));
  candidates.push(path.join(process.env.LOCALAPPDATA || "", "Programs", "Python", "Python312", "python.exe"));

  return [...new Set(candidates.filter(Boolean))];
}

function spawnFlaskWith(pythonExecutable) {
  const root = projectRoot();
  const appPy = path.join(root, "app.py");

  if (!fs.existsSync(appPy)) {
    throw new Error(`app.py não encontrado em ${appPy}`);
  }

  const env = {
    ...process.env,
    ETISUL_FLASK_PORT: PORT,
    ETISUL_FLASK_DEBUG: "0",
    PYTHONUNBUFFERED: "1"
  };

  return spawn(pythonExecutable, [appPy], {
    cwd: root,
    env,
    windowsHide: true,
    stdio: "ignore"
  });
}

async function startFlask() {
  if (await isServerReady()) return;

  const errors = [];

  for (const candidate of pythonCandidates()) {
    try {
      await tryStartFlaskWith(candidate);
      return;
    } catch (error) {
      errors.push({ candidate, error });
      stopFlask();
    }
  }

  throw new Error(pythonNotFoundMessage(errors));
}

function tryStartFlaskWith(candidate) {
  return new Promise((resolve, reject) => {
    let settled = false;
    let child = null;

    const finish = (callback, value) => {
      if (settled) return;
      settled = true;
      if (child) {
        child.removeListener("error", onError);
        child.removeListener("exit", onExit);
      }
      callback(value);
    };

    const onError = (error) => {
      const message =
        error.code === "ENOENT"
          ? `Python não encontrado usando o comando "${candidate}".`
          : `Falha ao iniciar Python usando "${candidate}": ${error.message}`;
      finish(reject, new Error(message));
    };

    const onExit = (code, signal) => {
      if (settled) return;
      const reason = signal ? `sinal ${signal}` : `código ${code}`;
      finish(reject, new Error(`O Python "${candidate}" encerrou antes do Flask iniciar (${reason}).`));
    };

    try {
      child = spawnFlaskWith(candidate);
      flaskProcess = child;
      child.once("error", onError);
      child.once("exit", onExit);
    } catch (error) {
      finish(reject, error);
      return;
    }

    waitForServer()
      .then(() => finish(resolve))
      .catch((error) => finish(reject, error));
  });
}

function stopFlask() {
  if (flaskProcess) {
    flaskProcess.kill();
    flaskProcess = null;
  }
}

function pythonNotFoundMessage(errors) {
  const attempted = errors.map(({ candidate }) => `- ${candidate}`).join("\n");

  return [
    "Não foi possível encontrar ou iniciar o Python para abrir o Etisul Admin.",
    "",
    "Tentativas realizadas:",
    attempted || "- python\n- py",
    "",
    "Instale o Python no Windows ou configure o caminho absoluto antes de abrir o app:",
    'ETISUL_PYTHON=C:\\Users\\Gabri\\AppData\\Local\\Programs\\Python\\Python314\\python.exe',
    "",
    "Depois confira se as dependências Flask/MySQL do projeto estão instaladas."
  ].join("\n");
}

function isServerReady() {
  return new Promise((resolve) => {
    const req = http.get(ADMIN_URL, (res) => {
      res.resume();
      resolve(res.statusCode >= 200 && res.statusCode < 500);
    });

    req.on("error", () => resolve(false));
    req.setTimeout(800, () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function waitForServer() {
  const started = Date.now();

  while (Date.now() - started < 25000) {
    if (await isServerReady()) return;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }

  throw new Error("O Flask não respondeu em tempo hábil.");
}

function createWindow() {
  mainWindow = new BrowserWindow({
    title: APP_NAME,
    width: 1280,
    height: 820,
    minWidth: 1040,
    minHeight: 700,
    backgroundColor: "#fff8f7",
    icon: path.join(__dirname, "assets", "etisul-admin.png"),
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  mainWindow.webContents.on("will-navigate", (event, targetUrl) => {
    if (isWhatsAppUrl(targetUrl)) {
      event.preventDefault();
      shell.openExternal(targetUrl);
      return;
    }

    if (!isAllowedAdminUrl(targetUrl)) {
      event.preventDefault();
      mainWindow.loadURL(ADMIN_HOME_URL);
    }
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (isWhatsAppUrl(url)) {
      shell.openExternal(url);
      return { action: "deny" };
    }

    if (isAllowedAdminUrl(url)) {
      return { action: "allow" };
    }

    mainWindow.loadURL(ADMIN_HOME_URL);
    return { action: "deny" };
  });

  mainWindow.loadURL(ADMIN_URL);
}

function setupAutoUpdater() {
  if (!app.isPackaged) return;

  autoUpdater.on("update-downloaded", () => {
    dialog
      .showMessageBox(mainWindow, {
        type: "info",
        title: "Atualização pronta",
        message: "Uma nova versão do Etisul Admin foi baixada.",
        detail: "O aplicativo pode reiniciar agora para instalar a atualização.",
        buttons: ["Reiniciar agora", "Depois"],
        defaultId: 0,
        cancelId: 1
      })
      .then(({ response }) => {
        if (response === 0) {
          stopFlask();
          autoUpdater.quitAndInstall();
        }
      });
  });

  autoUpdater.on("error", (error) => {
    console.error("Falha ao verificar atualizações:", error);
  });

  autoUpdater.checkForUpdates().catch((error) => {
    console.error("Falha ao iniciar verificação de atualização:", error);
  });
}

function isWhatsAppUrl(targetUrl) {
  try {
    const parsed = new URL(targetUrl);
    return ["wa.me", "api.whatsapp.com", "web.whatsapp.com"].includes(parsed.hostname);
  } catch {
    return false;
  }
}

function isAllowedAdminUrl(targetUrl) {
  try {
    const parsed = new URL(targetUrl);
    const isLocalFlask = parsed.hostname === "127.0.0.1" && parsed.port === String(PORT);
    const pathName = parsed.pathname;

    return (
      isLocalFlask &&
      (pathName === "/login" ||
        pathName === "/logout" ||
        pathName.startsWith("/admin") ||
        pathName.startsWith("/static") ||
        pathName.startsWith("/uploads"))
    );
  } catch {
    return false;
  }
}

app.whenReady().then(async () => {
  app.setName(APP_NAME);

  try {
    await startFlask();
    createWindow();
    setupAutoUpdater();
  } catch (error) {
    dialog.showErrorBox(
      "Erro ao iniciar Etisul Admin",
      `${error.message}\n\nVerifique se o Python, as dependências Flask/MySQL e o MySQL estão instalados.`
    );
    app.quit();
  }
});

app.on("window-all-closed", () => {
  stopFlask();
  app.quit();
});
