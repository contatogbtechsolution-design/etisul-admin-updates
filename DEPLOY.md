# Publicar o site Etisul

## O que muda fora do computador

No computador, o site usa `127.0.0.1`, que só abre na própria máquina. Para abrir no celular pela internet, publique o Flask em uma hospedagem e use um MySQL online.

## Variáveis necessárias

Configure na hospedagem:

```env
SECRET_KEY=uma-chave-grande-e-segura
DB_HOST=host-do-mysql
DB_PORT=3306
DB_USER=usuario-do-mysql
DB_PASSWORD=senha-do-mysql
DB_NAME=etisul_db
ETISUL_FLASK_HOST=0.0.0.0
ETISUL_FLASK_DEBUG=0
```

Em plataformas que definem `PORT` automaticamente, não precisa definir `ETISUL_FLASK_PORT`.

## Comando de produção

```bash
gunicorn app:app
```

## Banco de dados

Exporte o banco local `etisul_db` e importe no MySQL da hospedagem. Não apague tabelas antigas; o app simplificado apenas deixou de usar partes de envio/status/e-mail.

## App desktop

O desktop continua funcionando localmente com os valores padrão. Para servidor online, use variáveis de ambiente no provedor.

## Deploy automático

O pipeline completo de CI/CD está documentado em `CI_CD.md`.
