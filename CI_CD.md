# CI/CD do Etisul

## Arquitetura adotada

Este projeto tem dois produtos no mesmo repositório:

- `app.py`: site Flask com Gunicorn em produção.
- `desktop/etisul-admin`: aplicativo Electron que já usa `electron-updater`.

Cada `push` na branch `main` dispara dois fluxos:

1. **Deploy do site**: valida o Flask, envia os arquivos por SSH para o servidor Linux, instala dependências e reinicia o serviço `systemd`.
2. **Publicação do desktop**: compila o instalador Windows e publica uma nova release no repositório GitHub configurado em `package.json`, permitindo atualização automática no app instalado.

## Secrets necessários no GitHub

Cadastre em `Settings > Secrets and variables > Actions`:

### Site

- `SSH_HOST`: IP ou domínio do servidor.
- `SSH_PORT`: porta SSH, normalmente `22`.
- `SSH_USER`: usuário usado no deploy.
- `SSH_PRIVATE_KEY`: chave privada SSH sem senha usada pelo GitHub Actions.
- `DEPLOY_PATH`: pasta do projeto no servidor, por exemplo `/var/www/etisul`.
- `SERVICE_NAME`: nome do serviço `systemd`, por exemplo `etisul`.

### App desktop

- `DESKTOP_GH_TOKEN`: token com permissão para criar releases no repositório `contatogbtechsolution-design/etisul-admin-updates`.

## Variáveis de ambiente da aplicação

No servidor, crie `/var/www/etisul/.env` com:

```env
SECRET_KEY=gere-uma-chave-grande-e-segura
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=etisul_user
DB_PASSWORD=troque-esta-senha
DB_NAME=etisul_db
ETISUL_FLASK_HOST=0.0.0.0
ETISUL_FLASK_DEBUG=0

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
OUTLOOK_CLIENT_ID=
OUTLOOK_CLIENT_SECRET=
APPLE_CLIENT_ID=
APPLE_CLIENT_SECRET=

WHATSAPP_VERIFY_TOKEN=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
```

Para o desktop local, continuam úteis:

- `ETISUL_FLASK_PORT`
- `ETISUL_PYTHON`

## Preparação inicial do servidor

Exemplo para Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx
sudo mkdir -p /var/www/etisul
sudo chown -R www-data:www-data /var/www/etisul
```

Depois:

1. Copie `deploy/systemd/etisul.service` para `/etc/systemd/system/etisul.service`.
2. Ajuste `User`, `Group`, caminhos e, se necessário, número de workers.
3. Copie `deploy/nginx/etisul.conf` para `/etc/nginx/sites-available/etisul`.
4. Troque `server_name` pelo domínio real.
5. Ative os serviços:

```bash
sudo ln -s /etc/nginx/sites-available/etisul /etc/nginx/sites-enabled/etisul
sudo nginx -t
sudo systemctl daemon-reload
sudo systemctl enable --now etisul
sudo systemctl reload nginx
```

Se o usuário de deploy não for `www-data`, dê a ele permissão de escrita em `/var/www/etisul` e permissão controlada para reiniciar apenas o serviço `etisul`.

## Como testar

### Site

1. Faça uma alteração pequena no código ou template.
2. Envie para `main`.
3. Abra `Actions` no GitHub e acompanhe `Deploy do site`.
4. Confirme no servidor:

```bash
sudo systemctl status etisul
curl -I http://127.0.0.1:8000
```

5. Abra o domínio e confirme a mudança publicada.

### Desktop

1. Faça um `push` para `main`.
2. Aguarde `Publicar app desktop`.
3. Verifique se surgiu uma nova release no repositório de updates.
4. Abra uma versão instalada anterior do app.
5. O `electron-updater` deve encontrar a release, baixar a atualização e oferecer reinício para instalar.

## Observações importantes

- O workflow preserva `static/uploads/`, `static/profiles/` e `.env` no servidor para não apagar arquivos enviados por usuários nem segredos.
- O app desktop recebe uma versão automática baseada no número da execução do workflow, evitando publicar duas releases com o mesmo número.
- Se o repositório de releases do desktop for privado, o token precisa ter acesso explícito a ele.
- Se quiser publicar o desktop somente quando houver mudança real, depois podemos restringir o workflow por `paths`.
