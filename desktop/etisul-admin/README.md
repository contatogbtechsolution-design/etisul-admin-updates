# Etisul Admin Desktop

Aplicativo desktop instalável para Windows usando Electron.

## Tecnologia usada

- Electron para abrir uma janela desktop própria.
- Flask/MySQL continuam sendo o backend.
- O Electron inicia o `app.py` localmente e abre direto em `/login`.
- A navegação da janela fica limitada ao login administrativo e às rotas `/admin`.

## Requisitos no PC

- MySQL configurado com o banco `etisul_db`.
- Python com as dependências do projeto instaladas.
- Node.js para gerar o instalador.

Se o Python não estiver no PATH, configure:

```powershell
$env:ETISUL_PYTHON="C:\Users\Gabri\AppData\Local\Programs\Python\Python314\python.exe"
```

## Rodar em modo desenvolvimento

```powershell
cd desktop\etisul-admin
npm install
npm start
```

## Gerar instalador Windows

```powershell
cd desktop\etisul-admin
.\build-installer.ps1
```

O instalador será gerado em:

```text
desktop\etisul-admin\dist
```

Ao instalar, o Windows criará o atalho **Etisul Admin** na área de trabalho e no menu iniciar.

## Observações

- A janela abre direto no login administrativo.
- A área do cliente não faz parte do app desktop.
- A loja pública continua separada no projeto Flask.
