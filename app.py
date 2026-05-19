from flask import Flask, render_template, request, redirect, session, send_from_directory, url_for
import mysql.connector
import json
import os
import urllib.parse
import urllib.request
import base64
from uuid import uuid4
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash


def carregar_env(caminho):
    if not os.path.exists(caminho):
        return

    with open(caminho, "r", encoding="utf-8") as arquivo:
        for linha in arquivo:
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue

            chave, valor = linha.split("=", 1)
            chave = chave.strip()
            valor = valor.strip().strip('"').strip("'")
            if chave and chave not in os.environ:
                os.environ[chave] = valor


carregar_env(os.path.join(os.path.dirname(__file__), ".env"))

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "etisul_secret")
app.permanent_session_lifetime = timedelta(days=30)
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
app.config["PROFILE_UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "profiles")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "etisul_webhook")
WHATSAPP_ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
MAX_USUARIOS_CADASTRADOS = 2
USER_CARGOS_CADASTRAVEIS = ("admin", "chefe", "funcionario")
CATEGORIAS_PADRAO = (
    ("Etiquetas adesivas", "Etiquetas autoadesivas para identificação geral.", "Etiquetas"),
    ("Rótulos personalizados", "Rótulos sob medida para marcas, embalagens e produtos.", "Rótulos"),
    ("Etiquetas térmicas", "Etiquetas para impressão térmica direta, sem ribbon.", "Etiquetas térmicas"),
    ("Etiquetas para balança", "Etiquetas usadas em balanças comerciais e varejo alimentar.", "Automação comercial"),
    ("Etiquetas para código de barras", "Etiquetas para identificação, rastreio e leitura por código de barras.", "Código de barras"),
    ("Etiquetas industriais", "Etiquetas para ambientes industriais e aplicações técnicas.", "Identificação industrial"),
    ("Etiquetas para logística", "Etiquetas para expedição, transporte, estoque e armazenagem.", "Logística"),
    ("Etiquetas para alimentos", "Etiquetas para produtos alimentícios, validade, lote e embalagem.", "Alimentos"),
    ("Etiquetas para farmácia", "Etiquetas para farmácias, laboratórios e identificação de medicamentos.", "Farmácia"),
    ("Etiquetas para automação comercial", "Etiquetas para PDV, varejo, lojas, gôndolas e sistemas comerciais.", "Automação comercial"),
    ("Etiquetas BOPP", "Etiquetas em filme BOPP para rótulos e embalagens.", "Materiais sintéticos"),
    ("Etiquetas couchê", "Etiquetas em papel couchê para impressão por transferência térmica.", "Papéis"),
    ("Etiquetas vinil", "Etiquetas em vinil para maior resistência e comunicação visual.", "Materiais sintéticos"),
    ("Etiquetas poliéster", "Etiquetas resistentes para identificação técnica e industrial.", "Materiais sintéticos"),
    ("Etiquetas removíveis", "Etiquetas com adesivo removível para aplicações temporárias.", "Adesivos"),
    ("Etiquetas resistentes à água", "Etiquetas para umidade, refrigeração e aplicações externas.", "Resistência"),
    ("Etiquetas para congelados", "Etiquetas para baixa temperatura, alimentos e câmaras frias.", "Alimentos"),
    ("Etiquetas de patrimônio", "Etiquetas para controle patrimonial e inventário.", "Identificação patrimonial"),
    ("Ribbons", "Suprimentos para impressão por transferência térmica.", "Ribbons"),
    ("Ribbon cera", "Ribbon de cera para papel e aplicações gerais.", "Ribbons"),
    ("Ribbon resina", "Ribbon de resina para materiais sintéticos e alta resistência.", "Ribbons"),
    ("Ribbon misto", "Ribbon cera/resina para equilíbrio entre custo e resistência.", "Ribbons"),
    ("Ribbon colorido", "Ribbons coloridos e metálicos para destaque visual.", "Ribbons"),
    ("Bobinas", "Bobinas de papel, etiquetas e suprimentos em rolo.", "Bobinas"),
    ("Bobinas térmicas", "Bobinas térmicas para automação comercial, PDV e comprovantes.", "Bobinas"),
    ("Lacres", "Lacres adesivos, de segurança e identificação.", "Lacres"),
    ("Tags", "Tags para identificação, preço, estoque e produtos.", "Tags"),
    ("Materiais personalizados", "Produtos feitos sob medida conforme necessidade do cliente.", "Personalizados"),
    ("Impressoras térmicas", "Equipamentos para impressão de etiquetas, rótulos e códigos.", "Equipamentos"),
    ("Leitores de código de barras", "Equipamentos de leitura e automação comercial.", "Automação comercial"),
    ("Coletores de dados", "Equipamentos para estoque, inventário e rastreabilidade.", "Automação comercial"),
    ("Suprimentos para impressão", "Materiais de apoio para impressão e identificação.", "Suprimentos"),
    ("Outros", "Produtos relacionados que não se encaixam nas demais categorias.", "Outros"),
)
OAUTH_PROVIDERS = {
    "google": {
        "nome": "Google",
        "env": "GOOGLE",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
        "scope": "openid email profile"
    },
    "outlook": {
        "nome": "Outlook",
        "env": "OUTLOOK",
        "authorize_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "userinfo_url": "https://graph.microsoft.com/oidc/userinfo",
        "scope": "openid email profile"
    },
    "apple": {
        "nome": "Apple",
        "env": "APPLE",
        "authorize_url": "https://appleid.apple.com/auth/authorize",
        "token_url": "https://appleid.apple.com/auth/token",
        "userinfo_url": "",
        "scope": "name email"
    }
}

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["PROFILE_UPLOAD_FOLDER"], exist_ok=True)


def imagem_permitida(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def salvar_imagem_produto(imagem):
    if not imagem or imagem.filename == "":
        return ""

    if not imagem_permitida(imagem.filename):
        return None

    filename_seguro = secure_filename(imagem.filename)
    nome, extensao = os.path.splitext(filename_seguro)
    filename = f"{nome}_{uuid4().hex}{extensao.lower()}"
    caminho = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    imagem.save(caminho)
    return filename


def salvar_foto_perfil(imagem):
    if not imagem or imagem.filename == "":
        return ""

    if not imagem_permitida(imagem.filename):
        return None

    filename_seguro = secure_filename(imagem.filename)
    nome, extensao = os.path.splitext(filename_seguro)
    filename = f"perfil_{nome}_{uuid4().hex}{extensao.lower()}"
    caminho = os.path.join(app.config["PROFILE_UPLOAD_FOLDER"], filename)
    imagem.save(caminho)
    return filename


def buscar_usuario_logado():
    if "usuario" not in session:
        return None

    conexao = conectar_bd()
    cursor = conexao.cursor(dictionary=True)
    garantir_campos_busca_admin(cursor)
    conexao.commit()
    cursor.execute(
        "SELECT id, nome, usuario, cargo, foto_perfil FROM usuarios WHERE usuario = %s",
        (session["usuario"],)
    )
    usuario = cursor.fetchone()
    cursor.close()
    conexao.close()
    return usuario


def buscar_cliente_logado():
    if "cliente_id" not in session:
        return None

    conexao = conectar_bd()
    cursor = conexao.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, nome, email, telefone, endereco, cpf_cnpj, cidade, estado, cep FROM clientes WHERE id = %s",
        (session["cliente_id"],)
    )
    cliente = cursor.fetchone()
    cursor.close()
    conexao.close()
    return cliente


def exigir_cliente():
    return "cliente_id" in session


def senha_cliente_valida(senha):
    return (
        any(c.isalpha() for c in senha)
        and any(c.isdigit() for c in senha)
    )


def dados_conta_cliente():
    cliente_atual = buscar_cliente_logado()
    conexao = conectar_bd()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("SELECT * FROM enderecos WHERE cliente_id = %s ORDER BY id DESC", (session["cliente_id"],))
    enderecos = cursor.fetchall()

    cursor.execute(
        """
        SELECT p.id, p.data, p.valor_total, COUNT(i.id) AS total_itens
        FROM pedidos p
        LEFT JOIN itens_pedido i ON i.pedido_id = p.id
        WHERE p.cliente_id = %s
        GROUP BY p.id
        ORDER BY p.data DESC
        LIMIT 4
        """,
        (session["cliente_id"],)
    )
    pedidos = cursor.fetchall()

    cursor.close()
    conexao.close()

    return {
        "cliente": cliente_atual,
        "enderecos": enderecos,
        "pedidos": pedidos
    }


def resposta_bot_whatsapp(texto):
    texto = (texto or "").lower()

    if any(palavra in texto for palavra in ["orcamento", "orçamento", "pedido", "preço", "preco", "valor"]):
        return (
            "Olá! Recebemos sua solicitação de orçamento. "
            "Nossa equipe vai conferir os produtos e responder com os valores em breve. "
            "Se puder, envie também quantidade, medidas e tipo de etiqueta desejada."
        )

    if any(palavra in texto for palavra in ["prazo", "atendimento", "retorno"]):
        return (
            "Olá! O prazo depende do modelo, quantidade e detalhes do orçamento. "
            "Envie os detalhes do produto que você precisa para verificarmos certinho."
        )

    if any(palavra in texto for palavra in ["pagamento", "pix", "boleto", "cartão", "cartao"]):
        return (
            "A Etisul trabalha com orçamento personalizado. "
            "Nossa equipe informa as condições comerciais no atendimento."
        )

    return (
        "Olá! Obrigado por entrar em contato com a Etisul Etiquetas. "
        "Recebemos sua mensagem e logo nossa equipe vai responder. "
        "Para agilizar, envie o produto desejado, quantidade e telefone para contato."
    )


def enviar_mensagem_whatsapp(numero_destino, texto):
    if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        print("WhatsApp bot não configurado: defina WHATSAPP_ACCESS_TOKEN e WHATSAPP_PHONE_NUMBER_ID.")
        return False

    url = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": numero_destino,
        "type": "text",
        "text": {"body": texto}
    }
    dados = json.dumps(payload).encode("utf-8")
    requisicao = urllib.request.Request(
        url,
        data=dados,
        headers={
            "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(requisicao, timeout=10) as resposta:
            return 200 <= resposta.status < 300
    except Exception as erro:
        print(f"Erro ao enviar mensagem pelo WhatsApp: {erro}")
        return False


def gerar_link_whatsapp(numero_destino, mensagem):
    numero = "".join(filter(str.isdigit, numero_destino))
    texto = urllib.parse.quote(mensagem)
    return f"https://web.whatsapp.com/send?phone={numero}&text={texto}"


def conectar_bd():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ.get("DB_USER", "etisul_user"),
        password=os.environ.get("DB_PASSWORD", "123456"),
        database=os.environ.get("DB_NAME", "etisul_db")
    )


def coluna_existe(cursor, tabela, coluna):
    cursor.execute(f"SHOW COLUMNS FROM {tabela} LIKE %s", (coluna,))
    return cursor.fetchone() is not None


def termo_like(busca):
    return f"%{busca.strip().lower()}%"


def garantir_categorias_catalogo(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS categorias (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nome VARCHAR(120) NOT NULL UNIQUE,
            descricao TEXT NULL,
            tipo VARCHAR(80) NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    if not coluna_existe(cursor, "categorias", "tipo"):
        cursor.execute("ALTER TABLE categorias ADD COLUMN tipo VARCHAR(80) NULL")

    if not coluna_existe(cursor, "produtos", "categoria_id"):
        cursor.execute("ALTER TABLE produtos ADD COLUMN categoria_id INT NULL")

    for nome, descricao, tipo in CATEGORIAS_PADRAO:
        cursor.execute(
            """
            INSERT INTO categorias (nome, descricao, tipo)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                descricao = COALESCE(NULLIF(descricao, ''), VALUES(descricao)),
                tipo = COALESCE(NULLIF(tipo, ''), VALUES(tipo))
            """,
            (nome, descricao, tipo)
        )


def garantir_campos_busca_admin(cursor):
    if not coluna_existe(cursor, "clientes", "cpf_cnpj"):
        cursor.execute("ALTER TABLE clientes ADD COLUMN cpf_cnpj VARCHAR(30) NULL")
    if not coluna_existe(cursor, "clientes", "cidade"):
        cursor.execute("ALTER TABLE clientes ADD COLUMN cidade VARCHAR(120) NULL")
    if not coluna_existe(cursor, "clientes", "estado"):
        cursor.execute("ALTER TABLE clientes ADD COLUMN estado VARCHAR(80) NULL")
    if not coluna_existe(cursor, "clientes", "cep"):
        cursor.execute("ALTER TABLE clientes ADD COLUMN cep VARCHAR(20) NULL")

    if not coluna_existe(cursor, "usuarios", "email"):
        cursor.execute("ALTER TABLE usuarios ADD COLUMN email VARCHAR(160) NULL")

    if not coluna_existe(cursor, "usuarios", "telefone"):
        cursor.execute("ALTER TABLE usuarios ADD COLUMN telefone VARCHAR(30) NULL")

    if not coluna_existe(cursor, "usuarios", "status"):
        cursor.execute("ALTER TABLE usuarios ADD COLUMN status VARCHAR(30) DEFAULT 'ativo'")

    if not coluna_existe(cursor, "usuarios", "forcar_troca_senha"):
        cursor.execute("ALTER TABLE usuarios ADD COLUMN forcar_troca_senha TINYINT(1) DEFAULT 0")

    if not coluna_existe(cursor, "pedidos", "email_cliente"):
        cursor.execute("ALTER TABLE pedidos ADD COLUMN email_cliente VARCHAR(160) NULL")

    if not coluna_existe(cursor, "pedidos", "empresa"):
        cursor.execute("ALTER TABLE pedidos ADD COLUMN empresa VARCHAR(160) NULL")

    if not coluna_existe(cursor, "pedidos", "observacoes"):
        cursor.execute("ALTER TABLE pedidos ADD COLUMN observacoes TEXT NULL")

    if not coluna_existe(cursor, "pedidos", "status_orcamento"):
        cursor.execute("ALTER TABLE pedidos ADD COLUMN status_orcamento VARCHAR(30) DEFAULT 'em andamento'")

    if not coluna_existe(cursor, "pedidos", "valor_orcamento"):
        cursor.execute("ALTER TABLE pedidos ADD COLUMN valor_orcamento DECIMAL(10,2) NULL")

    if not coluna_existe(cursor, "pedidos", "encerrado_em"):
        cursor.execute("ALTER TABLE pedidos ADD COLUMN encerrado_em DATETIME NULL")

    if not coluna_existe(cursor, "pedidos", "envio_tipo"):
        cursor.execute("ALTER TABLE pedidos ADD COLUMN envio_tipo VARCHAR(120) NULL")

    if not coluna_existe(cursor, "pedidos", "pagamento_tipo_texto"):
        cursor.execute("ALTER TABLE pedidos ADD COLUMN pagamento_tipo_texto VARCHAR(120) NULL")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS contatos_whatsapp (
            id INT AUTO_INCREMENT PRIMARY KEY,
            origem VARCHAR(30) NOT NULL,
            nome VARCHAR(160) NOT NULL,
            email VARCHAR(160) NULL,
            telefone VARCHAR(30) NULL,
            mensagem TEXT NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS opcoes_recebimento (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nome VARCHAR(120) NOT NULL UNIQUE,
            descricao TEXT NULL,
            ativo TINYINT(1) NOT NULL DEFAULT 1,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        INSERT IGNORE INTO opcoes_recebimento (nome, descricao, ativo)
        VALUES ('Pagamento a combinar', 'Definido com o cliente durante o atendimento.', 1)
        """
    )
    cursor.execute("UPDATE usuarios SET nome = 'Suporte', cargo = 'admin' WHERE usuario = 'admin'")


def exigir_login():
    return "usuario" in session


def exigir_admin():
    return "usuario" in session and session.get("cargo") == "admin"


def exigir_admin_principal():
    return "usuario" in session and session.get("cargo") == "admin"


def exigir_chefe():
    return "usuario" in session and session.get("cargo") in ("admin", "chefe")


def oauth_provider_config(provider):
    config = OAUTH_PROVIDERS.get(provider)
    if not config:
        return None

    prefixo = config["env"]
    client_id = os.environ.get(f"{prefixo}_CLIENT_ID", "")
    client_secret = os.environ.get(f"{prefixo}_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        return None

    return {**config, "client_id": client_id, "client_secret": client_secret}


def oauth_redirect_uri(provider):
    return request.url_root.rstrip("/") + url_for("cliente_oauth_callback", provider=provider)


def decodificar_jwt_payload(token):
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        dados = base64.urlsafe_b64decode(payload.encode("utf-8"))
        return json.loads(dados.decode("utf-8"))
    except Exception:
        return {}


def oauth_post_token(config, provider, code):
    dados = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": oauth_redirect_uri(provider),
        "client_id": config["client_id"],
        "client_secret": config["client_secret"]
    }
    requisicao = urllib.request.Request(
        config["token_url"],
        data=urllib.parse.urlencode(dados).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST"
    )

    with urllib.request.urlopen(requisicao, timeout=15) as resposta:
        return json.loads(resposta.read().decode("utf-8"))


def oauth_buscar_perfil(config, token_data):
    access_token = token_data.get("access_token", "")
    perfil = {}

    if config.get("userinfo_url") and access_token:
        requisicao = urllib.request.Request(
            config["userinfo_url"],
            headers={"Authorization": f"Bearer {access_token}"}
        )
        with urllib.request.urlopen(requisicao, timeout=15) as resposta:
            perfil = json.loads(resposta.read().decode("utf-8"))

    if token_data.get("id_token"):
        perfil_token = decodificar_jwt_payload(token_data["id_token"])
        perfil = {**perfil_token, **perfil}

    return {
        "id": perfil.get("sub") or perfil.get("id"),
        "email": perfil.get("email") or perfil.get("preferred_username"),
        "nome": perfil.get("name") or perfil.get("given_name") or perfil.get("email", "").split("@")[0]
    }


def entrar_ou_criar_cliente_social(provider, perfil):
    email = (perfil.get("email") or "").strip().lower()
    oauth_subject = str(perfil.get("id") or "").strip()
    nome = (perfil.get("nome") or email.split("@")[0] or "Cliente Etisul").strip()

    if not email or not oauth_subject:
        return None, False

    conexao = conectar_bd()
    cursor = conexao.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM clientes WHERE oauth_provider = %s AND oauth_subject = %s",
        (provider, oauth_subject)
    )
    cliente_db = cursor.fetchone()
    criado = False

    if not cliente_db:
        cursor.execute("SELECT * FROM clientes WHERE email = %s", (email,))
        cliente_db = cursor.fetchone()

    if cliente_db:
        cursor.execute(
            "UPDATE clientes SET oauth_provider = %s, oauth_subject = %s, ultimo_login_social = NOW() WHERE id = %s",
            (provider, oauth_subject, cliente_db["id"])
        )
        cliente_id = cliente_db["id"]
    else:
        cursor.execute(
            """
            INSERT INTO clientes (nome, email, telefone, senha_hash, endereco, oauth_provider, oauth_subject, ultimo_login_social)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """,
            (nome, email, "", generate_password_hash(uuid4().hex), "", provider, oauth_subject)
        )
        cliente_id = cursor.lastrowid
        criado = True

    conexao.commit()
    cursor.close()
    conexao.close()

    return cliente_id, criado


@app.context_processor
def carrinho_context():
    carrinho = session.get("carrinho", {})
    total = sum(carrinho.values())
    return {
        "total_carrinho": total,
        "usuario_logado": buscar_usuario_logado(),
        "cliente_logado": buscar_cliente_logado()
    }


@app.route("/")
def home():
    admin_link = "/admin" if exigir_login() else "/login"
    return render_template("index.html", admin_link=admin_link)


@app.route("/esqueci-senha")
def esqueci_senha_admin():
    mensagem = "Olá, preciso redefinir a senha do acesso administrativo da Etisul."
    return render_template(
        "esqueci_senha.html",
        mensagem="Para redefinir a senha administrativa, fale com o responsável pelo sistema pelo WhatsApp.",
        whatsapp_link=gerar_link_whatsapp("5549999419541", mensagem),
        voltar_url="/login"
    )


@app.route("/cliente")
def cliente():
    return render_template("cliente.html")


@app.route("/cliente/cadastro", methods=["GET", "POST"])
def cliente_cadastro():
    if request.method == "POST":
        nome = request.form["nome"].strip()
        email = request.form["email"].strip().lower()
        telefone = request.form["telefone"].strip()
        cpf_cnpj = request.form["cpf_cnpj"].strip()
        cidade = request.form["cidade"].strip()
        estado = request.form["estado"].strip()
        cep = request.form["cep"].strip()
        senha = request.form["senha"]
        endereco = request.form.get("endereco", "").strip()

        if not nome or not email or not telefone or not cpf_cnpj or not cidade or not estado or not cep or not senha_cliente_valida(senha):
            return render_template("cliente_cadastro.html", erro="Crie uma senha usando letras e números.")

        conexao = conectar_bd()
        cursor = conexao.cursor(dictionary=True)
        garantir_campos_busca_admin(cursor)
        cursor.execute("SELECT id FROM clientes WHERE email = %s", (email,))
        cliente_existente = cursor.fetchone()

        if cliente_existente:
            cursor.close()
            conexao.close()
            return render_template("cliente_cadastro.html", erro="Este e-mail já está cadastrado.")

        cursor.execute(
            "INSERT INTO clientes (nome, email, telefone, senha_hash, endereco, cpf_cnpj, cidade, estado, cep) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (nome, email, telefone, generate_password_hash(senha), endereco, cpf_cnpj, cidade, estado, cep)
        )
        cliente_id = cursor.lastrowid

        if endereco:
            cursor.execute(
                "INSERT INTO enderecos (cliente_id, nome, rua, numero, cidade, estado) VALUES (%s, %s, %s, %s, %s, %s)",
                (cliente_id, "Principal", endereco, "S/N", cidade, estado)
            )

        conexao.commit()
        cursor.close()
        conexao.close()

        session.permanent = True
        session["cliente_id"] = cliente_id
        return redirect("/cliente/login")

    return render_template("cliente_cadastro.html")


@app.route("/cliente/login", methods=["GET", "POST"])
def cliente_login():
    if request.method == "GET" and exigir_cliente():
        return render_template("cliente_conta.html", **dados_conta_cliente())

    if request.method == "POST":
        email = request.form["email"].strip().lower()
        senha = request.form["senha"]
        destino = request.args.get("next") or "/cliente/login"

        conexao = conectar_bd()
        cursor = conexao.cursor(dictionary=True)
        cursor.execute("SELECT * FROM clientes WHERE email = %s", (email,))
        cliente_db = cursor.fetchone()
        cursor.close()
        conexao.close()

        if cliente_db and check_password_hash(cliente_db["senha_hash"], senha):
            session.permanent = True
            session["cliente_id"] = cliente_db["id"]
            return redirect(destino)

        return render_template("cliente_login.html", erro="E-mail ou senha inválidos.", email_digitado=email)

    mensagem = ""
    if request.args.get("senha_redefinida") == "1":
        mensagem = "Senha redefinida com sucesso. Entre usando sua nova senha."

    return render_template(
        "cliente_login.html",
        mensagem=mensagem,
        email_digitado=request.args.get("email", "").strip().lower()
    )


@app.route("/cliente/esqueci-senha", methods=["GET", "POST"])
def cliente_esqueci_senha():
    email = request.values.get("email", "").strip().lower()

    if request.method == "POST":
        senha = request.form.get("senha", "")
        confirmar = request.form.get("confirmar_senha", "")
        dados_formulario = {
            "email_digitado": email,
            "senha_digitada": senha,
            "confirmar_senha_digitada": confirmar
        }

        if not email or "@" not in email:
            return render_template(
                "redefinir_senha.html",
                erro="Informe o e-mail cadastrado.",
                **dados_formulario
            )

        if not senha_cliente_valida(senha):
            return render_template(
                "redefinir_senha.html",
                erro="Crie uma senha usando letras e números.",
                **dados_formulario
            )

        if senha != confirmar:
            return render_template(
                "redefinir_senha.html",
                erro="A confirmação da senha não confere.",
                **dados_formulario
            )

        conexao = conectar_bd()
        cursor = conexao.cursor(dictionary=True)
        cursor.execute("SELECT id FROM clientes WHERE email = %s", (email,))
        cliente_db = cursor.fetchone()

        if not cliente_db:
            cursor.close()
            conexao.close()
            return render_template(
                "redefinir_senha.html",
                erro="E-mail não encontrado no cadastro.",
                **dados_formulario
            )

        cursor.execute(
            "UPDATE clientes SET senha_hash = %s WHERE email = %s",
            (generate_password_hash(senha), email)
        )
        conexao.commit()
        cursor.close()
        conexao.close()

        return redirect(
            "/cliente/login?senha_redefinida=1&email="
            + urllib.parse.quote(email)
        )

    return render_template("redefinir_senha.html", email_digitado=email)


@app.route("/cliente/oauth/<provider>")
def cliente_oauth_login(provider):
    config = oauth_provider_config(provider)
    provider_info = OAUTH_PROVIDERS.get(provider)

    if not provider_info:
        return redirect("/cliente/login")

    if not config:
        return render_template("oauth_configuracao.html", provider=provider_info)

    state = uuid4().hex
    session.permanent = True
    session["oauth_state"] = state
    session["oauth_provider"] = provider

    parametros = {
        "client_id": config["client_id"],
        "redirect_uri": oauth_redirect_uri(provider),
        "response_type": "code",
        "scope": config["scope"],
        "state": state
    }

    if provider == "apple":
        parametros["response_mode"] = "form_post"

    return redirect(config["authorize_url"] + "?" + urllib.parse.urlencode(parametros))


@app.route("/cliente/oauth/<provider>/callback", methods=["GET", "POST"])
def cliente_oauth_callback(provider):
    config = oauth_provider_config(provider)
    provider_info = OAUTH_PROVIDERS.get(provider)

    if not provider_info or not config:
        return redirect("/cliente/login")

    state = request.values.get("state", "")
    code = request.values.get("code", "")

    if not state or state != session.get("oauth_state") or provider != session.get("oauth_provider"):
        return render_template("cliente_login.html", erro="Não foi possível validar o login social. Tente novamente.")

    if not code:
        return render_template("cliente_login.html", erro="Login social cancelado ou sem autorização.")

    try:
        token_data = oauth_post_token(config, provider, code)
        perfil = oauth_buscar_perfil(config, token_data)
        cliente_id, criado = entrar_ou_criar_cliente_social(provider, perfil)
    except Exception as erro:
        print(f"Erro no login OAuth {provider}: {erro}")
        return render_template("cliente_login.html", erro="Não foi possível concluir o login social agora.")

    if not cliente_id:
        return render_template("cliente_login.html", erro="A conta social não retornou e-mail válido.")

    session.pop("oauth_state", None)
    session.pop("oauth_provider", None)
    session.permanent = True
    session["cliente_id"] = cliente_id

    return redirect("/cliente/login")


@app.route("/cliente/logout")
def cliente_logout():
    session.pop("cliente_id", None)
    return redirect("/")


@app.route("/cliente/editar", methods=["GET", "POST"])
def cliente_editar():
    if not exigir_cliente():
        return redirect("/cliente/login")

    if request.method == "POST":
        nome = request.form["nome"].strip()
        telefone = request.form["telefone"].strip()
        cpf_cnpj = request.form["cpf_cnpj"].strip()
        cidade = request.form["cidade"].strip()
        estado = request.form["estado"].strip()
        cep = request.form["cep"].strip()
        endereco = request.form.get("endereco", "").strip()
        senha = request.form.get("senha", "")

        conexao = conectar_bd()
        cursor = conexao.cursor()

        if senha:
            cursor.execute(
                "UPDATE clientes SET nome = %s, telefone = %s, endereco = %s, cpf_cnpj = %s, cidade = %s, estado = %s, cep = %s, senha_hash = %s WHERE id = %s",
                (nome, telefone, endereco, cpf_cnpj, cidade, estado, cep, generate_password_hash(senha), session["cliente_id"])
            )
        else:
            cursor.execute(
                "UPDATE clientes SET nome = %s, telefone = %s, endereco = %s, cpf_cnpj = %s, cidade = %s, estado = %s, cep = %s WHERE id = %s",
                (nome, telefone, endereco, cpf_cnpj, cidade, estado, cep, session["cliente_id"])
            )

        conexao.commit()
        cursor.close()
        conexao.close()
        return redirect("/cliente")

    return render_template("cliente_editar.html", cliente=buscar_cliente_logado())


@app.route("/cliente/pedidos")
def cliente_pedidos():
    if not exigir_cliente():
        return redirect("/cliente/login")

    conexao = conectar_bd()
    cursor = conexao.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT p.id AS pedido_id, p.data, p.valor_total,
               pr.nome AS produto, pr.imagem, i.produto_id, i.quantidade, i.preco_unitario
        FROM pedidos p
        JOIN itens_pedido i ON i.pedido_id = p.id
        JOIN produtos pr ON pr.id = i.produto_id
        WHERE p.cliente_id = %s
        ORDER BY p.data DESC, i.id ASC
        """,
        (session["cliente_id"],)
    )
    itens = cursor.fetchall()
    cursor.close()
    conexao.close()

    pedidos = {}
    for item in itens:
        pedido_id = item["pedido_id"]
        if pedido_id not in pedidos:
            pedidos[pedido_id] = {
                "id": pedido_id,
                "data": item["data"],
                "valor_total": item["valor_total"],
                "itens": []
            }
        pedidos[pedido_id]["itens"].append(item)

    return render_template("cliente_pedidos.html", pedidos=pedidos.values())


@app.route("/cliente/pedidos/<int:id>")
def cliente_pedido_detalhes(id):
    if not exigir_cliente():
        return redirect("/cliente/login")

    conexao = conectar_bd()
    cursor = conexao.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT p.*, e.rua, e.numero, e.cidade, e.estado, f.tipo AS pagamento_tipo,
               f.bandeira, f.ultimos4, f.nome_titular
        FROM pedidos p
        LEFT JOIN enderecos e ON e.id = p.endereco_id
        LEFT JOIN formas_pagamento f ON f.id = p.forma_pagamento_id
        WHERE p.id = %s AND p.cliente_id = %s
        """,
        (id, session["cliente_id"])
    )
    pedido = cursor.fetchone()

    cursor.execute(
        """
        SELECT i.*, pr.nome, pr.imagem
        FROM itens_pedido i
        JOIN produtos pr ON pr.id = i.produto_id
        WHERE i.pedido_id = %s
        """,
        (id,)
    )
    itens = cursor.fetchall()
    cursor.close()
    conexao.close()

    if not pedido:
        return redirect("/cliente/pedidos")

    return render_template("cliente_pedido_detalhes.html", pedido=pedido, itens=itens)


@app.route("/cliente/comprar-novamente/<int:id>")
def comprar_novamente(id):
    return redirect("/produtos")


@app.route("/sobre-empresa")
def sobre_empresa():
    admin_link = "/admin" if exigir_login() else "/login"
    return render_template("sobre_empresa.html", admin_link=admin_link)


@app.route("/produtos")
def produtos():
    busca = request.args.get("busca", "")

    conexao = conectar_bd()
    cursor = conexao.cursor(dictionary=True)
    garantir_categorias_catalogo(cursor)
    conexao.commit()

    if busca:
        cursor.execute(
            """
            SELECT p.*, c.nome AS categoria_nome
            FROM produtos p
            LEFT JOIN categorias c ON c.id = p.categoria_id
            WHERE p.nome LIKE %s
              AND p.id NOT IN (SELECT produto_id FROM produtos_ocultos_catalogo)
            """,
            (f"%{busca}%",)
        )
    else:
        cursor.execute(
            """
            SELECT p.*, c.nome AS categoria_nome
            FROM produtos p
            LEFT JOIN categorias c ON c.id = p.categoria_id
            WHERE p.id NOT IN (SELECT produto_id FROM produtos_ocultos_catalogo)
            """
        )

    produtos = cursor.fetchall()

    cursor.close()
    conexao.close()

    return render_template("produtos.html", produtos=produtos, busca=busca)


@app.route("/produtos/<int:id>")
def produto_detalhe(id):
    conexao = conectar_bd()
    cursor = conexao.cursor(dictionary=True)
    garantir_categorias_catalogo(cursor)
    cursor.execute(
        """
        SELECT p.*, c.nome AS categoria_nome
        FROM produtos p
        LEFT JOIN categorias c ON c.id = p.categoria_id
        WHERE p.id = %s
          AND p.id NOT IN (SELECT produto_id FROM produtos_ocultos_catalogo)
        """,
        (id,),
    )
    produto = cursor.fetchone()
    conexao.commit()
    cursor.close()
    conexao.close()
    if not produto:
        return redirect("/produtos")
    return render_template("produto_detalhe.html", produto=produto)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        senha = request.form["senha"]

        conexao = conectar_bd()
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM usuarios WHERE usuario=%s AND senha=%s",
            (usuario, senha)
        )
        user = cursor.fetchone()
        cursor.close()
        conexao.close()

        if user and (user.get("status") or "ativo") == "ativo":
            session["usuario"] = user["usuario"]
            session["cargo"] = user["cargo"]
            if user.get("forcar_troca_senha"):
                return redirect("/admin/configuracoes")
            return redirect("/admin")

        return "Login inválido ou usuário inativo"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/admin")
def admin():
    if not exigir_login():
        return redirect("/login")

    conexao = conectar_bd()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total FROM produtos WHERE id NOT IN (SELECT produto_id FROM produtos_ocultos_catalogo)")
    total_produtos = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) AS total FROM pedidos")
    total_pedidos = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) AS total FROM clientes")
    total_clientes = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) AS total FROM usuarios WHERE cargo <> 'admin'")
    total_funcionarios = cursor.fetchone()["total"]

    cursor.execute(
        """
        SELECT p.id, p.nome_cliente, p.valor_total, p.data
        FROM pedidos p
        ORDER BY p.data DESC
        LIMIT 5
        """
    )
    pedidos_recentes = cursor.fetchall()

    cursor.close()
    conexao.close()

    return render_template(
        "admin.html",
        total_produtos=total_produtos,
        total_pedidos=total_pedidos,
        total_clientes=total_clientes,
        total_funcionarios=total_funcionarios,
        pedidos_recentes=pedidos_recentes
    )


@app.route("/admin/dados-bancarios", methods=["GET", "POST"])
def admin_dados_bancarios():
    return redirect("/admin/whatsapp")

    conexao = conectar_bd()
    cursor = conexao.cursor(dictionary=True)

    if request.method == "POST":
        cursor.execute(
            """
            UPDATE dados_bancarios_loja
            SET banco = %s, agencia = %s, conta = %s, tipo_conta = %s, chave_pix = %s,
                documento_recebedor = %s, nome_titular = %s, email_financeiro = %s
            WHERE id = 1
            """,
            (
                request.form.get("banco", ""),
                request.form.get("agencia", ""),
                request.form.get("conta", ""),
                request.form.get("tipo_conta", ""),
                request.form.get("chave_pix", ""),
                request.form.get("documento_recebedor", ""),
                request.form.get("nome_titular", ""),
                request.form.get("email_financeiro", "")
            )
        )
        conexao.commit()

    cursor.execute("SELECT * FROM dados_bancarios_loja WHERE id = 1")
    dados = cursor.fetchone()
    cursor.close()
    conexao.close()

    return render_template("admin_dados_bancarios.html", dados=dados)


@app.route("/admin/categorias")
def admin_categorias():
    if not exigir_chefe():
        return "Acesso negado: apenas admin ou chefe podem acessar categorias.", 403

    busca = request.args.get("busca", "").strip()
    conexao = conectar_bd()
    cursor = conexao.cursor(dictionary=True)
    garantir_categorias_catalogo(cursor)
    conexao.commit()

    consulta = """
        SELECT c.*, COUNT(p.id) AS total_produtos
        FROM categorias c
        LEFT JOIN produtos p
          ON p.categoria_id = c.id
         AND p.id NOT IN (SELECT produto_id FROM produtos_ocultos_catalogo)
    """
    params = []

    if busca:
        termo = termo_like(busca)
        consulta += """
            WHERE LOWER(c.nome) LIKE %s
               OR LOWER(COALESCE(c.descricao, '')) LIKE %s
               OR LOWER(COALESCE(c.tipo, '')) LIKE %s
        """
        params.extend([termo, termo, termo])

    consulta += """
        GROUP BY c.id, c.nome, c.descricao, c.tipo, c.criado_em
        ORDER BY c.nome
    """
    cursor.execute(consulta, params)
    categorias = cursor.fetchall()
    cursor.close()
    conexao.close()

    return render_template("admin_categorias.html", categorias=categorias, busca=busca)


@app.route("/admin/categorias/add", methods=["POST"])
def add_categoria():
    if not exigir_chefe():
        return "Acesso negado: apenas admin ou chefe podem cadastrar categorias.", 403

    nome = request.form.get("nome", "").strip()
    descricao = request.form.get("descricao", "").strip()
    tipo = request.form.get("tipo", "").strip()

    if not nome:
        return redirect("/admin/categorias")

    conexao = conectar_bd()
    cursor = conexao.cursor()
    garantir_categorias_catalogo(cursor)
    cursor.execute(
        """
        INSERT INTO categorias (nome, descricao, tipo)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE descricao = VALUES(descricao), tipo = VALUES(tipo)
        """,
        (nome, descricao, tipo)
    )
    conexao.commit()
    cursor.close()
    conexao.close()

    return redirect("/admin/categorias")


@app.route("/admin/categorias/edit/<int:id>", methods=["GET", "POST"])
def edit_categoria(id):
    if not exigir_chefe():
        return "Acesso negado: apenas admin ou chefe podem editar categorias.", 403

    conexao = conectar_bd()
    cursor = conexao.cursor(dictionary=True)
    garantir_categorias_catalogo(cursor)

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        descricao = request.form.get("descricao", "").strip()
        tipo = request.form.get("tipo", "").strip()

        if nome:
            cursor.execute(
                "UPDATE categorias SET nome = %s, descricao = %s, tipo = %s WHERE id = %s",
                (nome, descricao, tipo, id)
            )
            conexao.commit()
        cursor.close()
        conexao.close()
        return redirect("/admin/categorias")

    cursor.execute("SELECT * FROM categorias WHERE id = %s", (id,))
    categoria = cursor.fetchone()
    cursor.close()
    conexao.close()
    if not categoria:
        return redirect("/admin/categorias")
    return render_template("edit_categoria.html", categoria=categoria)


@app.route("/admin/categorias/delete/<int:id>", methods=["POST"])
def delete_categoria(id):
    if not exigir_chefe():
        return "Acesso negado: apenas admin ou chefe podem excluir categorias.", 403

    conexao = conectar_bd()
    cursor = conexao.cursor()
    garantir_categorias_catalogo(cursor)
    cursor.execute("UPDATE produtos SET categoria_id = NULL WHERE categoria_id = %s", (id,))
    cursor.execute("DELETE FROM categorias WHERE id = %s", (id,))
    conexao.commit()
    cursor.close()
    conexao.close()

    return redirect("/admin/categorias")


@app.route("/admin/categorias/delete-all", methods=["POST"])
def delete_todas_categorias():
    if not exigir_chefe():
        return "Acesso negado: apenas admin ou chefe podem excluir categorias.", 403

    conexao = conectar_bd()
    cursor = conexao.cursor()
    garantir_categorias_catalogo(cursor)
    cursor.execute("UPDATE produtos SET categoria_id = NULL")
    cursor.execute("DELETE FROM categorias")
    conexao.commit()
    cursor.close()
    conexao.close()

    return redirect("/admin/categorias")


@app.route("/admin/clientes")
def admin_clientes():
    if not exigir_admin():
        return "Acesso negado: apenas admin pode acessar clientes cadastrados.", 403

    busca = request.args.get("busca", "").strip()
    conexao = conectar_bd()
    cursor = conexao.cursor(dictionary=True)
    garantir_campos_busca_admin(cursor)
    conexao.commit()

    consulta = """
        SELECT
            c.id,
            c.nome,
            c.email,
            c.telefone,
            c.cpf_cnpj,
            c.endereco,
            c.criado_em,
            GROUP_CONCAT(DISTINCT e.cidade SEPARATOR ', ') AS cidades
        FROM clientes c
        LEFT JOIN enderecos e ON e.cliente_id = c.id
    """
    params = []

    if busca:
        termo = termo_like(busca)
        consulta += """
            WHERE CAST(c.id AS CHAR) LIKE %s
               OR LOWER(c.nome) LIKE %s
               OR LOWER(c.email) LIKE %s
               OR LOWER(COALESCE(c.telefone, '')) LIKE %s
               OR LOWER(COALESCE(c.cpf_cnpj, '')) LIKE %s
               OR LOWER(COALESCE(c.endereco, '')) LIKE %s
               OR LOWER(COALESCE(e.cidade, '')) LIKE %s
        """
        params.extend([termo, termo, termo, termo, termo, termo, termo])

    consulta += """
        GROUP BY c.id, c.nome, c.email, c.telefone, c.cpf_cnpj, c.endereco, c.criado_em
        ORDER BY c.criado_em DESC
    """
    cursor.execute(consulta, params)
    clientes = cursor.fetchall()
    cursor.close()
    conexao.close()
    return render_template("admin_clientes.html", clientes=clientes, busca=busca)


@app.route("/admin/clientes/<int:id>")
def admin_cliente_detalhes(id):
    if not exigir_admin():
        return "Acesso negado: apenas admin pode acessar clientes cadastrados.", 403
    conexao = conectar_bd()
    cursor = conexao.cursor(dictionary=True)
    garantir_campos_busca_admin(cursor)
    cursor.execute("SELECT * FROM clientes WHERE id = %s", (id,))
    cliente = cursor.fetchone()
    cursor.execute("SELECT * FROM enderecos WHERE cliente_id = %s ORDER BY id DESC", (id,))
    enderecos = cursor.fetchall()
    cursor.close()
    conexao.close()
    if not cliente:
        return redirect("/admin/clientes")
    return render_template("admin_cliente_detalhes.html", cliente=cliente, enderecos=enderecos)


@app.route("/admin/formas-pagamento")
def admin_formas_pagamento():
    return redirect("/admin/opcoes-recebimento")


@app.route("/admin/opcoes-recebimento", methods=["GET", "POST"])
def admin_opcoes_recebimento():
    if not exigir_admin():
        return "Acesso negado: apenas admin pode acessar opções de recebimento.", 403

    conexao = conectar_bd()
    cursor = conexao.cursor(dictionary=True)
    garantir_campos_busca_admin(cursor)

    if request.method == "POST":
        cursor.execute(
            """
            INSERT INTO opcoes_recebimento (nome, descricao, ativo)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE descricao = VALUES(descricao), ativo = VALUES(ativo)
            """,
            (
                request.form.get("nome", "").strip(),
                request.form.get("descricao", "").strip(),
                1 if request.form.get("ativo") == "1" else 0,
            ),
        )
        conexao.commit()
        cursor.close()
        conexao.close()
        return redirect("/admin/opcoes-recebimento")

    cursor.execute("SELECT * FROM opcoes_recebimento ORDER BY ativo DESC, nome")
    opcoes = cursor.fetchall()
    conexao.commit()
    cursor.close()
    conexao.close()
    return render_template("admin_opcoes_recebimento.html", opcoes=opcoes)


@app.route("/admin/opcoes-recebimento/edit/<int:id>", methods=["POST"])
def admin_editar_opcao_recebimento(id):
    if not exigir_admin():
        return "Acesso negado: apenas admin pode alterar opções de recebimento.", 403
    conexao = conectar_bd()
    cursor = conexao.cursor()
    garantir_campos_busca_admin(cursor)
    cursor.execute(
        """
        UPDATE opcoes_recebimento
        SET nome = %s, descricao = %s, ativo = %s
        WHERE id = %s
        """,
        (
            request.form.get("nome", "").strip(),
            request.form.get("descricao", "").strip(),
            1 if request.form.get("ativo") == "1" else 0,
            id,
        ),
    )
    conexao.commit()
    cursor.close()
    conexao.close()
    return redirect("/admin/opcoes-recebimento")


@app.route("/admin/opcoes-recebimento/delete/<int:id>", methods=["POST"])
def admin_excluir_opcao_recebimento(id):
    if not exigir_admin():
        return "Acesso negado: apenas admin pode excluir opções de recebimento.", 403
    conexao = conectar_bd()
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM opcoes_recebimento WHERE id = %s", (id,))
    conexao.commit()
    cursor.close()
    conexao.close()
    return redirect("/admin/opcoes-recebimento")


@app.route("/admin/relatorios")
def admin_relatorios():
    if not exigir_admin():
        return "Acesso negado: apenas admin pode acessar relatórios.", 403

    mes_filtro = request.args.get("mes", "").strip()
    ano_filtro = request.args.get("ano", "").strip()
    conexao = conectar_bd()
    cursor = conexao.cursor(dictionary=True)
    garantir_campos_busca_admin(cursor)
    conexao.commit()
    garantir_campos_busca_admin(cursor)
    cursor.execute("SELECT COUNT(*) AS total FROM pedidos WHERE status_orcamento IN ('fechado', 'cancelado')")
    total_orcamentos = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) AS total FROM pedidos WHERE status_orcamento = 'fechado'")
    total_fechados = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) AS total FROM pedidos WHERE status_orcamento = 'cancelado'")
    total_cancelados = cursor.fetchone()["total"]
    cursor.execute("SELECT COALESCE(SUM(valor_orcamento), 0) AS total FROM pedidos WHERE status_orcamento = 'fechado'")
    total_lucrado = cursor.fetchone()["total"]
    cursor.execute("SELECT COALESCE(SUM(valor_orcamento), 0) AS total FROM pedidos WHERE status_orcamento = 'cancelado'")
    total_perdido = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) AS total FROM clientes")
    total_clientes = cursor.fetchone()["total"]
    filtro_sql = ""
    filtro_params = []
    if mes_filtro and ano_filtro:
        filtro_sql = " AND DATE_FORMAT(COALESCE(encerrado_em, data), '%Y-%m') = %s"
        filtro_params.append(f"{ano_filtro}-{mes_filtro.zfill(2)}")
    cursor.execute(
        """
        SELECT DATE_FORMAT(COALESCE(encerrado_em, data), '%Y-%m') AS mes,
               SUM(CASE WHEN status_orcamento = 'fechado' THEN valor_orcamento ELSE 0 END) AS fechado,
               SUM(CASE WHEN status_orcamento = 'cancelado' THEN valor_orcamento ELSE 0 END) AS cancelado
        FROM pedidos
        WHERE status_orcamento IN ('fechado', 'cancelado')
        """ + filtro_sql + """
        GROUP BY mes
        ORDER BY mes
        """,
        filtro_params
    )
    meses = cursor.fetchall()
    cursor.close()
    conexao.close()
    return render_template(
        "admin_relatorios.html",
        total_orcamentos=total_orcamentos,
        total_fechados=total_fechados,
        total_cancelados=total_cancelados,
        total_lucrado=total_lucrado,
        total_perdido=total_perdido,
        total_clientes=total_clientes,
        meses=meses,
        mes_filtro=mes_filtro,
        ano_filtro=ano_filtro
    )


@app.route("/admin/whatsapp")
def admin_whatsapp():
    if not exigir_login():
        return redirect("/login")

    busca = request.args.get("busca", "").strip()
    conexao = conectar_bd()
    cursor = conexao.cursor(dictionary=True)
    garantir_campos_busca_admin(cursor)

    consulta = """
        SELECT
            p.id,
            p.nome_cliente,
            p.telefone,
            p.quantidade,
            p.valor_total,
            p.data,
            c.email AS cliente_email,
            GROUP_CONCAT(CONCAT(pr.nome, ' (', i.quantidade, ')') SEPARATOR ', ') AS produtos
        FROM pedidos p
        LEFT JOIN clientes c ON c.id = p.cliente_id
        LEFT JOIN itens_pedido i ON i.pedido_id = p.id
        LEFT JOIN produtos pr ON pr.id = i.produto_id
    """
    params = []

    if busca:
        termo = f"%{busca}%"
        consulta += """
            WHERE p.nome_cliente LIKE %s
                OR p.telefone LIKE %s
                OR c.email LIKE %s
                OR pr.nome LIKE %s
                OR p.id = %s
        """
        params.extend([termo, termo, termo, termo, int(busca) if busca.isdigit() else -1])

    consulta += """
        GROUP BY p.id, p.nome_cliente, p.telefone, p.quantidade, p.valor_total,
            p.data, c.email
        ORDER BY p.data DESC
        LIMIT 80
    """
    cursor.execute(consulta, params)
    orcamentos = cursor.fetchall()
    cursor.close()
    conexao.close()

    return render_template("admin_whatsapp.html", orcamentos=orcamentos, busca=busca)


@app.route("/admin/whatsapp-duvidas")
def admin_whatsapp_duvidas():
    if not exigir_login():
        return redirect("/login")

    busca = request.args.get("busca", "").strip()
    conexao = conectar_bd()
    cursor = conexao.cursor(dictionary=True)
    garantir_campos_busca_admin(cursor)
    consulta = "SELECT * FROM contatos_whatsapp WHERE origem = 'duvida'"
    params = []
    if busca:
        termo = termo_like(busca)
        consulta += " AND (LOWER(nome) LIKE %s OR LOWER(COALESCE(email, '')) LIKE %s OR LOWER(COALESCE(telefone, '')) LIKE %s OR LOWER(mensagem) LIKE %s)"
        params.extend([termo, termo, termo, termo])
    consulta += " ORDER BY criado_em DESC LIMIT 80"
    cursor.execute(consulta, params)
    duvidas = cursor.fetchall()
    cursor.close()
    conexao.close()
    return render_template("admin_whatsapp_duvidas.html", duvidas=duvidas, busca=busca)


@app.route("/admin/configuracoes", methods=["GET", "POST"])
def admin_configuracoes():
    if not exigir_login():
        return redirect("/login")

    mensagem = ""
    erro = ""
    usuario_logado = buscar_usuario_logado()

    if request.method == "POST":
        senha_atual = request.form.get("senha_atual", "")
        nova_senha = request.form.get("nova_senha", "")
        confirmar_senha = request.form.get("confirmar_senha", "")
        foto = request.files.get("foto_perfil")
        remover_foto = request.form.get("remover_foto") == "1"

        conexao = conectar_bd()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute(
            "SELECT id, senha FROM usuarios WHERE usuario = %s",
            (session["usuario"],)
        )
        usuario_senha = cursor.fetchone()

        if nova_senha:
            if not senha_atual:
                erro = "Informe a senha atual para trocar a senha."
            elif not usuario_senha or usuario_senha["senha"] != senha_atual:
                erro = "Senha atual incorreta."
            elif nova_senha != confirmar_senha:
                erro = "A confirmação da nova senha não confere."
            else:
                cursor.execute(
                    "UPDATE usuarios SET senha = %s, forcar_troca_senha = 0 WHERE usuario = %s",
                    (nova_senha, session["usuario"])
                )
                conexao.commit()
                mensagem = "Senha alterada com sucesso."

        if not erro and remover_foto:
            cursor.execute(
                "UPDATE usuarios SET foto_perfil = NULL WHERE usuario = %s",
                (session["usuario"],)
            )
            conexao.commit()
            mensagem = "Foto removida com sucesso."
        elif not erro and foto and foto.filename:
            filename = salvar_foto_perfil(foto)

            if filename is None:
                erro = "Formato de foto inválido. Use PNG, JPG, JPEG, GIF ou WEBP."
            else:
                cursor.execute(
                    "UPDATE usuarios SET foto_perfil = %s WHERE usuario = %s",
                    (filename, session["usuario"])
                )
                conexao.commit()
                mensagem = "Configurações salvas com sucesso."

        cursor.close()
        conexao.close()
        usuario_logado = buscar_usuario_logado()

    return render_template(
        "admin_configuracoes.html",
        usuario=usuario_logado,
        mensagem=mensagem,
        erro=erro
    )


@app.route("/admin/usuarios", methods=["GET", "POST"])
def admin_usuarios():
    if not exigir_login():
        return redirect("/login")

    if not exigir_admin():
        return "Acesso negado: apenas usuários admin podem gerenciar usuários.", 403

    mensagem = ""
    erro = ""
    busca = request.args.get("busca", "").strip()

    conexao = conectar_bd()
    cursor = conexao.cursor(dictionary=True)

    if request.method == "POST":
        nome = request.form["nome"].strip()
        usuario = request.form["usuario"].strip()
        senha = request.form["senha"].strip()
        cargo = request.form["cargo"]

        cursor.execute("SELECT COUNT(*) AS total FROM usuarios WHERE cargo <> 'admin'")
        total_usuarios = cursor.fetchone()["total"]

        if cargo != "admin" and total_usuarios >= MAX_USUARIOS_CADASTRADOS:
            erro = "Limite de 2 usuários cadastrados atingido."
        elif not nome or not usuario or not senha:
            erro = "Informe nome, usuário e senha."
        elif cargo not in USER_CARGOS_CADASTRAVEIS:
            erro = "Cargo inválido."
        else:
            cursor.execute("SELECT id FROM usuarios WHERE usuario = %s", (usuario,))
            usuario_existente = cursor.fetchone()

            if usuario_existente:
                erro = "Esse nome de usuário já existe."
            else:
                cursor.execute(
                    "INSERT INTO usuarios (nome, usuario, senha, cargo, forcar_troca_senha) VALUES (%s, %s, %s, %s, %s)",
                    (nome, usuario, senha, cargo, 1)
                )
                conexao.commit()
                mensagem = "Usuário cadastrado com sucesso."

    consulta = "SELECT id, nome, usuario, cargo, email, telefone, status FROM usuarios"
    params = []

    if busca:
        termo = termo_like(busca)
        consulta += """
            WHERE CAST(id AS CHAR) LIKE %s
               OR LOWER(nome) LIKE %s
               OR LOWER(usuario) LIKE %s
               OR LOWER(cargo) LIKE %s
               OR LOWER(COALESCE(email, '')) LIKE %s
               OR LOWER(COALESCE(telefone, '')) LIKE %s
               OR LOWER(COALESCE(status, 'ativo')) LIKE %s
        """
        params.extend([termo, termo, termo, termo, termo, termo, termo])

    consulta += " ORDER BY id"
    cursor.execute(consulta, params)
    usuarios = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) AS total FROM usuarios WHERE cargo <> 'admin'")
    total_usuarios = cursor.fetchone()["total"]

    cursor.close()
    conexao.close()

    return render_template(
        "admin_usuarios.html",
        usuarios=usuarios,
        cargos=USER_CARGOS_CADASTRAVEIS,
        max_usuarios=MAX_USUARIOS_CADASTRADOS,
        total_usuarios=total_usuarios,
        mensagem=mensagem,
        erro=erro,
        busca=busca
    )


@app.route("/admin/usuarios/edit/<int:id>", methods=["GET", "POST"])
def edit_usuario(id):
    if not exigir_login():
        return redirect("/login")

    if not exigir_admin():
        return "Acesso negado: apenas usuários admin podem editar usuários.", 403

    conexao = conectar_bd()
    cursor = conexao.cursor(dictionary=True)
    mensagem = ""
    erro = ""

    garantir_campos_busca_admin(cursor)
    cursor.execute("SELECT id, nome, usuario, cargo, status FROM usuarios WHERE id = %s", (id,))
    usuario_editado = cursor.fetchone()

    if not usuario_editado:
        cursor.close()
        conexao.close()
        return redirect("/admin/usuarios")

    if usuario_editado["usuario"] == "admin":
        cursor.close()
        conexao.close()
        return "O admin principal não pode ser editado por esta tela.", 403

    if request.method == "POST":
        nome = request.form["nome"].strip()
        usuario = request.form["usuario"].strip()
        cargo = request.form["cargo"]
        status = request.form.get("status", "ativo")
        nova_senha = request.form.get("senha", "").strip()

        if not nome or not usuario:
            erro = "Informe nome e usuário."
        elif cargo not in USER_CARGOS_CADASTRAVEIS or status not in ("ativo", "inativo"):
            erro = "Cargo inválido."
        else:
            cursor.execute(
                "SELECT id FROM usuarios WHERE usuario = %s AND id <> %s",
                (usuario, id)
            )
            usuario_existente = cursor.fetchone()

            if usuario_existente:
                erro = "Esse nome de usuário já está em uso."
            else:
                if nova_senha:
                    cursor.execute(
                        "UPDATE usuarios SET nome = %s, usuario = %s, cargo = %s, status = %s, senha = %s WHERE id = %s",
                        (nome, usuario, cargo, status, nova_senha, id)
                    )
                else:
                    cursor.execute(
                        "UPDATE usuarios SET nome = %s, usuario = %s, cargo = %s, status = %s WHERE id = %s",
                        (nome, usuario, cargo, status, id)
                    )

                conexao.commit()
                mensagem = "Usuário atualizado com sucesso."
                cursor.execute("SELECT id, nome, usuario, cargo, status FROM usuarios WHERE id = %s", (id,))
                usuario_editado = cursor.fetchone()

    cursor.close()
    conexao.close()

    return render_template(
        "edit_usuario.html",
        usuario_editado=usuario_editado,
        cargos=USER_CARGOS_CADASTRAVEIS,
        mensagem=mensagem,
        erro=erro
    )


@app.route("/admin/usuarios/delete/<int:id>")
def delete_usuario(id):
    if not exigir_login():
        return redirect("/login")

    if not exigir_admin():
        return "Acesso negado: apenas usuários admin podem remover usuários.", 403

    conexao = conectar_bd()
    cursor = conexao.cursor(dictionary=True)
    cursor.execute("SELECT usuario, cargo FROM usuarios WHERE id = %s", (id,))
    usuario = cursor.fetchone()

    if usuario and usuario["usuario"] != "admin" and usuario["usuario"] != session.get("usuario"):
        cursor.execute("DELETE FROM usuarios WHERE id = %s", (id,))
        conexao.commit()

    cursor.close()
    conexao.close()

    return redirect("/admin/usuarios")


@app.route("/admin/produtos")
def admin_produtos():
    if not exigir_login():
        return redirect("/login")

    busca = request.args.get("busca", "").strip()
    conexao = conectar_bd()
    cursor = conexao.cursor(dictionary=True)
    garantir_categorias_catalogo(cursor)
    conexao.commit()

    consulta = """
        SELECT p.*, c.nome AS categoria_nome
        FROM produtos p
        LEFT JOIN categorias c ON c.id = p.categoria_id
        WHERE p.id NOT IN (SELECT produto_id FROM produtos_ocultos_catalogo)
    """
    params = []

    if busca:
        termo = termo_like(busca)
        consulta += """
            AND (
                CAST(p.id AS CHAR) LIKE %s
                OR LOWER(p.nome) LIKE %s
                OR LOWER(COALESCE(p.descricao, '')) LIKE %s
                OR LOWER(COALESCE(c.nome, '')) LIKE %s
                OR CAST(p.preco AS CHAR) LIKE %s
                OR LOWER('ativo') LIKE %s
            )
        """
        params.extend([termo, termo, termo, termo, termo, termo])

    consulta += " ORDER BY p.id DESC"
    cursor.execute(consulta, params)
    produtos = cursor.fetchall()
    cursor.execute("SELECT id, nome FROM categorias ORDER BY nome")
    categorias = cursor.fetchall()
    cursor.close()
    conexao.close()

    return render_template("admin_produtos.html", produtos=produtos, categorias=categorias, busca=busca)


@app.route("/admin/produtos/add", methods=["POST"])
def add_produto():
    if not exigir_chefe():
        return "Acesso negado"

    nome = request.form["nome"]
    descricao = request.form["descricao"]
    categoria_id = request.form.get("categoria_id") or None
    imagem = request.files.get("imagem")

    filename = salvar_imagem_produto(imagem)
    if filename is None:
        return "Formato de imagem inválido. Use PNG, JPG, JPEG, GIF ou WEBP.", 400

    conexao = conectar_bd()
    cursor = conexao.cursor()
    garantir_categorias_catalogo(cursor)

    cursor.execute(
        "INSERT INTO produtos (nome, preco, descricao, imagem, estoque, categoria_id) VALUES (%s, %s, %s, %s, %s, %s)",
        (nome, 0, descricao, filename, 0, categoria_id)
    )

    conexao.commit()
    cursor.close()
    conexao.close()

    return redirect("/admin/produtos")


@app.route("/admin/produtos/edit/<int:id>", methods=["GET", "POST"])
def edit_produto(id):
    if not exigir_chefe():
        return "Acesso negado: apenas admin ou chefe podem editar produtos.", 403

    conexao = conectar_bd()
    cursor = conexao.cursor(dictionary=True)
    garantir_categorias_catalogo(cursor)
    conexao.commit()

    if request.method == "POST":
        nome = request.form["nome"]
        descricao = request.form["descricao"]
        categoria_id = request.form.get("categoria_id") or None
        imagem = request.files.get("imagem")
        filename = salvar_imagem_produto(imagem)

        if filename is None:
            cursor.close()
            conexao.close()
            return "Formato de imagem inválido. Use PNG, JPG, JPEG, GIF ou WEBP.", 400

        if filename:
            cursor.execute(
                "UPDATE produtos SET nome = %s, descricao = %s, imagem = %s, categoria_id = %s WHERE id = %s",
                (nome, descricao, filename, categoria_id, id)
            )
        else:
            cursor.execute(
                "UPDATE produtos SET nome = %s, descricao = %s, categoria_id = %s WHERE id = %s",
                (nome, descricao, categoria_id, id)
            )

        conexao.commit()
        cursor.close()
        conexao.close()

        return redirect("/admin/produtos")

    cursor.execute("SELECT * FROM produtos WHERE id = %s", (id,))
    produto = cursor.fetchone()
    cursor.execute("SELECT id, nome FROM categorias ORDER BY nome")
    categorias = cursor.fetchall()

    cursor.close()
    conexao.close()

    return render_template("edit_produto.html", produto=produto, categorias=categorias)


@app.route("/admin/produtos/remove-image/<int:id>", methods=["POST"])
def remover_imagem_produto(id):
    if not exigir_chefe():
        return "Acesso negado: apenas admin ou chefe podem remover imagens.", 403

    conexao = conectar_bd()
    cursor = conexao.cursor()
    cursor.execute("UPDATE produtos SET imagem = '' WHERE id = %s", (id,))
    conexao.commit()
    cursor.close()
    conexao.close()
    return redirect(f"/admin/produtos/edit/{id}")


@app.route("/admin/produtos/delete/<int:id>")
def delete_produto(id):
    if not exigir_chefe():
        return "Acesso negado: apenas o chefe pode excluir produtos."

    conexao = conectar_bd()
    cursor = conexao.cursor()
    cursor.execute("INSERT IGNORE INTO produtos_ocultos_catalogo (produto_id) VALUES (%s)", (id,))
    conexao.commit()
    cursor.close()
    conexao.close()

    return redirect("/admin/produtos")


@app.route("/admin/produtos/delete-all", methods=["POST"])
def delete_todos_produtos():
    if not exigir_chefe():
        return "Acesso negado: apenas admin ou chefe podem excluir produtos.", 403

    conexao = conectar_bd()
    cursor = conexao.cursor()
    cursor.execute(
        """
        INSERT IGNORE INTO produtos_ocultos_catalogo (produto_id)
        SELECT id FROM produtos
        """
    )
    conexao.commit()
    cursor.close()
    conexao.close()

    return redirect("/admin/produtos")


@app.route("/carrinho/add/<int:id>", methods=["POST"])
def adicionar_carrinho(id):
    quantidade = max(1, int(request.form.get("quantidade", 1)))
    carrinho = session.get("carrinho", {})
    carrinho[str(id)] = carrinho.get(str(id), 0) + quantidade
    session["carrinho"] = carrinho
    destino = request.form.get("next") or request.referrer or "/produtos"
    separador = "&" if "?" in destino else "?"
    return redirect(f"{destino}{separador}carrinho=adicionado")


@app.route("/carrinho")
def carrinho():
    carrinho = session.get("carrinho", {})
    produtos = []
    opcoes_recebimento = []
    if carrinho:
        conexao = conectar_bd()
        cursor = conexao.cursor(dictionary=True)
        garantir_campos_busca_admin(cursor)
        ids = list(carrinho.keys())
        placeholders = ",".join(["%s"] * len(ids))
        cursor.execute(f"SELECT id, nome, imagem, descricao FROM produtos WHERE id IN ({placeholders})", ids)
        produtos_db = {str(produto["id"]): produto for produto in cursor.fetchall()}
        cursor.execute("SELECT nome FROM opcoes_recebimento WHERE ativo = 1 ORDER BY nome")
        opcoes_recebimento = cursor.fetchall()
        conexao.commit()
        cursor.close()
        conexao.close()
        for produto_id, quantidade in carrinho.items():
            produto = produtos_db.get(produto_id)
            if produto:
                produto["quantidade"] = quantidade
                produtos.append(produto)
    return render_template("carrinho.html", produtos=produtos, opcoes_recebimento=opcoes_recebimento)


@app.route("/carrinho/opcoes", methods=["POST"])
def carrinho_opcoes():
    session["envio_tipo"] = request.form.get("envio_tipo", "")
    session["pagamento_tipo"] = request.form.get("pagamento_tipo", "")
    return redirect("/finalizar")


@app.route("/carrinho/atualizar/<int:id>", methods=["POST"])
def atualizar_carrinho(id):
    carrinho = session.get("carrinho", {})
    quantidade = int(request.form.get("quantidade", 1))
    if quantidade <= 0:
        carrinho.pop(str(id), None)
    else:
        carrinho[str(id)] = quantidade
    session["carrinho"] = carrinho
    return redirect("/carrinho")


@app.route("/carrinho/remover/<int:id>")
def remover_carrinho(id):
    carrinho = session.get("carrinho", {})
    carrinho.pop(str(id), None)
    session["carrinho"] = carrinho
    return redirect("/carrinho")


@app.route("/finalizar", methods=["GET", "POST"])
def finalizar():
    if not exigir_cliente():
        return redirect("/cliente/login?next=/finalizar")

    carrinho = session.get("carrinho", {})
    cliente_atual = buscar_cliente_logado()
    produtos_carrinho = []
    if carrinho:
        conexao_resumo = conectar_bd()
        cursor_resumo = conexao_resumo.cursor(dictionary=True)
        ids = list(carrinho.keys())
        placeholders = ",".join(["%s"] * len(ids))
        cursor_resumo.execute(f"SELECT id, nome, imagem, descricao FROM produtos WHERE id IN ({placeholders})", ids)
        produtos_db = {str(produto["id"]): produto for produto in cursor_resumo.fetchall()}
        cursor_resumo.close()
        conexao_resumo.close()
        for produto_id, quantidade in carrinho.items():
            produto = produtos_db.get(produto_id)
            if produto:
                produto["quantidade"] = quantidade
                produtos_carrinho.append(produto)

    if request.method == "POST" and carrinho:
        conexao = conectar_bd()
        cursor = conexao.cursor(dictionary=True)
        garantir_campos_busca_admin(cursor)
        primeiro_id = int(next(iter(carrinho)))
        total_quantidade = sum(carrinho.values())
        cursor.execute(
            """
            INSERT INTO pedidos (
                produto_id, cliente_id, nome_cliente, telefone, quantidade, valor_total, status,
                email_cliente, observacoes, status_orcamento, envio_tipo, pagamento_tipo_texto
            ) VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, 'em andamento', %s, %s)
            """,
            (
                primeiro_id,
                cliente_atual["id"],
                cliente_atual["nome"],
                cliente_atual["telefone"],
                total_quantidade,
                "compra online",
                cliente_atual["email"],
                request.form.get("observacoes", "").strip(),
                session.get("envio_tipo", ""),
                session.get("pagamento_tipo", ""),
            ),
        )
        pedido_id = cursor.lastrowid
        produtos_mensagem = []
        for produto_id, quantidade in carrinho.items():
            cursor.execute("SELECT nome FROM produtos WHERE id = %s", (produto_id,))
            produto = cursor.fetchone()
            cursor.execute(
                "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (%s, %s, %s, 0)",
                (pedido_id, produto_id, quantidade),
            )
            if produto:
                produtos_mensagem.append(f"{produto['nome']} x {quantidade}")
        mensagem_orcamento = (
            f"Orçamento solicitado #{pedido_id}: "
            + ", ".join(produtos_mensagem)
            + f". Entrega: {session.get('envio_tipo', 'A combinar')}. "
            + f"Pagamento: {session.get('pagamento_tipo', 'A combinar')}."
        )
        cursor.execute(
            "INSERT INTO contatos_whatsapp (origem, nome, email, telefone, mensagem) VALUES (%s, %s, %s, %s, %s)",
            ("orcamento", cliente_atual["nome"], cliente_atual["email"], cliente_atual["telefone"], mensagem_orcamento),
        )
        conexao.commit()
        cursor.close()
        conexao.close()
        session.pop("carrinho", None)
        session.pop("envio_tipo", None)
        session.pop("pagamento_tipo", None)
        return render_template(
            "whatsapp_enviado.html",
            sucesso_contato="Compra enviada para orçamento com sucesso.",
            tipo_confirmacao="compra",
            numero_pedido=pedido_id,
        )

    return render_template(
        "finalizar.html",
        cliente=cliente_atual,
        carrinho=carrinho,
        produtos=produtos_carrinho,
        envio_tipo=session.get("envio_tipo", "Entrega a combinar"),
        pagamento_tipo=session.get("pagamento_tipo", "Pagamento a combinar"),
    )

@app.route("/boleto/<int:id>")
def boleto(id):
    return redirect("/produtos")


@app.route("/pedido/<int:id>", methods=["GET", "POST"])
def pedido(id):
    if request.method == "POST":
        nome = request.form["nome"]
        telefone = request.form["telefone"]
        email = request.form["email"]
        empresa = request.form.get("empresa", "")
        quantidade = request.form["quantidade"]
        observacoes = request.form.get("observacoes", "")

        conexao = conectar_bd()
        cursor = conexao.cursor(dictionary=True)

        garantir_campos_busca_admin(cursor)
        cursor.execute("SELECT nome FROM produtos WHERE id = %s", (id,))
        produto = cursor.fetchone()
        nome_produto = produto["nome"] if produto else f"Produto {id}"

        cursor.execute(
            """
            INSERT INTO pedidos (
                produto_id, nome_cliente, telefone, quantidade, valor_total, status,
                email_cliente, empresa, observacoes, status_orcamento
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (id, nome, telefone, quantidade, 0, "pedido recebido", email, empresa, observacoes, "em andamento")
        )
        pedido_id = cursor.lastrowid

        if produto:
            cursor.execute(
                "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (%s, %s, %s, %s)",
                (pedido_id, id, quantidade, 0)
            )
        mensagem_orcamento = (
            f"Orçamento solicitado #{pedido_id}: {nome_produto} x {quantidade}. "
            f"Cliente: {nome}. Telefone: {telefone}. E-mail: {email}."
        )
        if empresa:
            mensagem_orcamento += f" Empresa: {empresa}."
        if observacoes:
            mensagem_orcamento += f" Observações: {observacoes}"
        cursor.execute(
            "INSERT INTO contatos_whatsapp (origem, nome, email, telefone, mensagem) VALUES (%s, %s, %s, %s, %s)",
            ("orcamento", nome, email, telefone, mensagem_orcamento)
        )

        conexao.commit()
        cursor.close()
        conexao.close()

        mensagem = (
            f"Olá, gostaria de solicitar o orçamento #{pedido_id}:\n\n"
            f"- {nome_produto} | Quantidade: {quantidade}\n\n"
            f"Nome: {nome}\nTelefone: {telefone}"
            f"\nE-mail: {email}"
        )

        if empresa:
            mensagem += f"\nEmpresa: {empresa}"

        if observacoes:
            mensagem += f"\nObservações: {observacoes}"

        link = gerar_link_whatsapp("5549999419541", mensagem)

        return render_template(
            "whatsapp_enviado.html",
            whatsapp_link=link,
            tipo_confirmacao="orcamento",
            numero_pedido=pedido_id,
            sucesso_contato="Seu orçamento foi registrado no sistema. Se quiser, finalize também pelo WhatsApp com a mensagem pronta."
        )

    return render_template("pedido.html", id=id)


@app.route("/duvidas", methods=["POST"])
def duvidas():
    nome = request.form.get("nome", "").strip()
    email = request.form.get("email", "").strip()
    telefone = request.form.get("telefone", "").strip()
    duvida = request.form.get("duvida", "").strip()

    if not nome or not email or not telefone or not duvida:
        return render_template(
            "whatsapp_enviado.html",
            erro_contato="Preencha nome, e-mail, telefone e mensagem antes de enviar."
        )

    if "@" not in email or "." not in email.split("@")[-1]:
        return render_template(
            "whatsapp_enviado.html",
            erro_contato="Informe um e-mail válido para que possamos responder sua dúvida."
        )

    mensagem = (
        "Olá, tenho uma dúvida pelo site:\n\n"
        f"Nome: {nome}\n"
        f"E-mail: {email}\n"
        f"Telefone: {telefone}\n\n"
        f"Dúvida: {duvida}"
    )
    conexao = conectar_bd()
    cursor = conexao.cursor()
    garantir_campos_busca_admin(cursor)
    cursor.execute(
        "INSERT INTO contatos_whatsapp (origem, nome, email, telefone, mensagem) VALUES (%s, %s, %s, %s, %s)",
        ("duvida", nome, email, telefone, duvida)
    )
    conexao.commit()
    cursor.close()
    conexao.close()
    link = gerar_link_whatsapp("5549999419541", mensagem)

    return render_template(
        "whatsapp_enviado.html",
        whatsapp_link=link
    )


@app.route("/admin/pedidos")
def admin_pedidos():
    if "usuario" not in session:
        return redirect("/login")

    busca = request.args.get("busca", "").strip()
    conexao = conectar_bd()
    cursor = conexao.cursor(dictionary=True)

    garantir_campos_busca_admin(cursor)
    conexao.commit()
    consulta = """
        SELECT
            p.id,
            pr.nome AS produto,
            p.nome_cliente,
            p.telefone,
            p.quantidade,
            p.valor_total,
            p.status,
            p.status_orcamento,
            p.data
        FROM pedidos p
        JOIN produtos pr ON p.produto_id = pr.id
        WHERE COALESCE(p.status_orcamento, 'em andamento') = 'em andamento'
    """
    params = []

    if busca:
        termo = termo_like(busca)
        consulta += """
            AND (
               CAST(p.id AS CHAR) LIKE %s
               OR LOWER(p.nome_cliente) LIKE %s
               OR LOWER(COALESCE(pr.nome, '')) LIKE %s
               OR LOWER(COALESCE(p.status, '')) LIKE %s
               OR CAST(p.data AS CHAR) LIKE %s
               OR CAST(COALESCE(p.valor_total, 0) AS CHAR) LIKE %s
               OR LOWER(COALESCE(p.telefone, '')) LIKE %s
               OR LOWER('orçamento') LIKE %s
               OR LOWER('retirada entrega a combinar') LIKE %s
            )
        """
        params.extend([termo, termo, termo, termo, termo, termo, termo, termo, termo])

    consulta += " ORDER BY p.data DESC"
    cursor.execute(consulta, params)

    pedidos = cursor.fetchall()

    cursor.close()
    conexao.close()

    return render_template("admin_pedido.html", pedidos=pedidos, busca=busca)


@app.route("/admin/orcamentos/<int:id>", methods=["GET", "POST"])
def admin_orcamento_detalhes(id):
    if not exigir_login():
        return redirect("/login")

    conexao = conectar_bd()
    cursor = conexao.cursor(dictionary=True)
    garantir_campos_busca_admin(cursor)

    if request.method == "POST":
        status_orcamento = request.form.get("status_orcamento", "em andamento")
        valor_orcamento = request.form.get("valor_orcamento", "").strip() or None
        if status_orcamento in ("fechado", "cancelado") and valor_orcamento is not None:
            cursor.execute(
                """
                UPDATE pedidos
                SET status_orcamento = %s, valor_orcamento = %s, encerrado_em = NOW()
                WHERE id = %s
                """,
                (status_orcamento, valor_orcamento, id)
            )
            conexao.commit()
            cursor.close()
            conexao.close()
            return redirect("/admin/pedidos-encerrados")

    cursor.execute("SELECT * FROM pedidos WHERE id = %s", (id,))
    orcamento = cursor.fetchone()
    cursor.execute(
        """
        SELECT pr.nome, i.quantidade
        FROM itens_pedido i
        JOIN produtos pr ON pr.id = i.produto_id
        WHERE i.pedido_id = %s
        """,
        (id,)
    )
    itens = cursor.fetchall()
    cursor.close()
    conexao.close()
    if not orcamento:
        return redirect("/admin/pedidos")
    return render_template("admin_orcamento_detalhes.html", orcamento=orcamento, itens=itens)


@app.route("/admin/pedidos-encerrados")
def admin_pedidos_encerrados():
    if not exigir_login():
        return redirect("/login")

    busca = request.args.get("busca", "").strip()
    conexao = conectar_bd()
    cursor = conexao.cursor(dictionary=True)
    garantir_campos_busca_admin(cursor)
    consulta = """
        SELECT p.id, pr.nome AS produto, p.nome_cliente, p.telefone, p.quantidade,
               p.data, p.status_orcamento, p.valor_orcamento
        FROM pedidos p
        JOIN produtos pr ON pr.id = p.produto_id
        WHERE COALESCE(p.status_orcamento, 'em andamento') IN ('fechado', 'cancelado')
    """
    params = []
    if busca:
        termo = termo_like(busca)
        consulta += """
            AND (
                CAST(p.id AS CHAR) LIKE %s OR LOWER(pr.nome) LIKE %s
                OR LOWER(p.nome_cliente) LIKE %s OR LOWER(p.status_orcamento) LIKE %s
            )
        """
        params.extend([termo, termo, termo, termo])
    consulta += " ORDER BY COALESCE(p.encerrado_em, p.data) DESC"
    cursor.execute(consulta, params)
    pedidos = cursor.fetchall()
    cursor.close()
    conexao.close()
    return render_template("admin_pedidos_encerrados.html", pedidos=pedidos, busca=busca)


@app.route("/webhook/whatsapp", methods=["GET", "POST"])
def webhook_whatsapp():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
            return challenge or "", 200

        return "Token de verificação inválido", 403

    dados = request.get_json(silent=True) or {}

    try:
        entries = dados.get("entry", [])
        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                messages = value.get("messages", [])

                for message in messages:
                    numero_cliente = message.get("from")
                    texto_cliente = message.get("text", {}).get("body", "")

                    if numero_cliente and texto_cliente:
                        resposta = resposta_bot_whatsapp(texto_cliente)
                        enviar_mensagem_whatsapp(numero_cliente, resposta)
    except Exception as erro:
        print(f"Erro ao processar webhook do WhatsApp: {erro}")

    return "EVENT_RECEIVED", 200


@app.route("/sw-admin.js")
def sw_admin():
    return send_from_directory(app.static_folder, "sw-admin.js")


if __name__ == "__main__":
    porta = int(os.environ.get("ETISUL_FLASK_PORT") or os.environ.get("PORT", "5000"))
    host = os.environ.get("ETISUL_FLASK_HOST", "127.0.0.1")
    debug = os.environ.get("ETISUL_FLASK_DEBUG", "0") == "1"
    app.run(host=host, port=porta, debug=debug, use_reloader=False)
