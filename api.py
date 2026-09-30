import os
import secrets
import smtplib
import sqlite3
from datetime import datetime, timedelta
from email.message import EmailMessage

from flask import Flask, g, jsonify, request
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash

try:
    from dotenv import load_dotenv
    load_dotenv()  # lê as configurações do arquivo .env, se existir
except ImportError:
    pass

BANCO = "safe_financas.db"  # arquivo criado automaticamente ao lado do api.py

# Configuração de e-mail (vem do arquivo .env)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USUARIO = os.getenv("SMTP_USUARIO", "")
SMTP_SENHA = os.getenv("SMTP_SENHA", "")

VALIDADE_CODIGO_MIN = 15
MAX_TENTATIVAS = 5
FORMATO_DATA = "%Y-%m-%d %H:%M:%S"

app = Flask(__name__)
CORS(app)


# --- BANCO DE DADOS ---
def criar_tabelas():
    db = sqlite3.connect(BANCO)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            nome       TEXT NOT NULL,
            email      TEXT NOT NULL UNIQUE,
            senha_hash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessoes (
            token      TEXT PRIMARY KEY,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id)
        );
        CREATE TABLE IF NOT EXISTS codigos_reset (
            usuario_id  INTEGER PRIMARY KEY REFERENCES usuarios(id),
            codigo_hash TEXT NOT NULL,
            expira_em   TEXT NOT NULL,
            tentativas  INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS transacoes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
            tipo       TEXT NOT NULL CHECK (tipo IN ('Renda', 'Despesa')),
            valor      REAL NOT NULL,
            descricao  TEXT NOT NULL,
            categoria  TEXT NOT NULL,
            data       TEXT NOT NULL
        );
    """)
    db.close()


def banco():
    if "db" not in g:
        g.db = sqlite3.connect(BANCO)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def fechar_banco(_):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# --- AJUDANTES ---
def erro(msg, codigo=400):
    return jsonify(erro=msg), codigo


def criar_sessao(usuario_id):
    token = secrets.token_hex(24)
    banco().execute("INSERT INTO sessoes (token, usuario_id) VALUES (?, ?)", (token, usuario_id))
    banco().commit()
    return token


def token_da_requisicao():
    return request.headers.get("Authorization", "").removeprefix("Bearer ").strip()


def usuario_logado():
    return banco().execute(
        "SELECT u.* FROM sessoes s JOIN usuarios u ON u.id = s.usuario_id WHERE s.token = ?",
        (token_da_requisicao(),),
    ).fetchone()


# --- ROTAS ---
@app.post("/api/cadastro")
def cadastro():
    d = request.get_json() or {}
    nome = d.get("nome", "").strip()
    email = d.get("email", "").strip().lower()
    senha = d.get("senha", "")
    if not (nome and email and senha):
        return erro("Preencha nome, e-mail e senha.")
    if "@" not in email or "." not in email:
        return erro("Digite um e-mail válido.")
    if len(senha) < 6:
        return erro("A senha precisa ter pelo menos 6 caracteres.")
    try:
        cur = banco().execute(
            "INSERT INTO usuarios (nome, email, senha_hash) VALUES (?, ?, ?)",
            (nome, email, generate_password_hash(senha)),
        )
        banco().commit()
    except sqlite3.IntegrityError:
        return erro("Já existe uma conta com esse e-mail.", 409)
    return jsonify(nome=nome, email=email, token=criar_sessao(cur.lastrowid))


@app.post("/api/login")
def login():
    d = request.get_json() or {}
    u = banco().execute(
        "SELECT * FROM usuarios WHERE email = ?", (d.get("email", "").strip().lower(),)
    ).fetchone()
    if u is None or not check_password_hash(u["senha_hash"], d.get("senha", "")):
        return erro("E-mail ou senha incorretos.", 401)
    return jsonify(nome=u["nome"], email=u["email"], token=criar_sessao(u["id"]))


@app.post("/api/logout")
def logout():
    banco().execute("DELETE FROM sessoes WHERE token = ?", (token_da_requisicao(),))
    banco().commit()
    return jsonify(ok=True)


@app.get("/api/resumo")
def resumo():
    u = usuario_logado()
    if u is None:
        return erro("Sessão expirada. Faça login de novo.", 401)
    linhas = banco().execute(
        "SELECT tipo, valor, descricao, categoria, data FROM transacoes "
        "WHERE usuario_id = ? ORDER BY data DESC, id DESC",
        (u["id"],),
    ).fetchall()
    saldo = sum(l["valor"] if l["tipo"] == "Renda" else -l["valor"] for l in linhas)
    transacoes = [
        {**dict(l), "data": datetime.strptime(l["data"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")}
        for l in linhas
    ]
    return jsonify(saldo=saldo, transacoes=transacoes)


@app.post("/api/transacoes")
def nova_transacao():
    u = usuario_logado()
    if u is None:
        return erro("Sessão expirada. Faça login de novo.", 401)
    d = request.get_json() or {}
    tipo = d.get("tipo")
    if tipo not in ("Renda", "Despesa"):
        return erro("Tipo inválido.")
    try:
        valor = round(float(d.get("valor")), 2)
    except (TypeError, ValueError):
        return erro("Digite um valor válido.")
    if valor <= 0:
        return erro("O valor precisa ser maior que zero.")

    banco().execute(
        "INSERT INTO transacoes (usuario_id, tipo, valor, descricao, categoria, data) VALUES (?, ?, ?, ?, ?, ?)",
        (
            u["id"], tipo, valor,
            d.get("descricao", "").strip() or "Sem descrição",
            d.get("categoria", "").strip() or "Geral",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    banco().commit()
    return jsonify(ok=True)


# --- ESQUECI MINHA SENHA ---
def enviar_codigo_por_email(destino, nome, codigo):
    if not (SMTP_USUARIO and SMTP_SENHA):
        # Sem e-mail configurado: mostra o código aqui no terminal (bom para testar)
        print(f"\n[MODO TESTE] E-mail não configurado. Código para {destino}: {codigo}\n")
        return
    msg = EmailMessage()
    msg["Subject"] = "Safe Finanças - código para redefinir sua senha"
    msg["From"] = SMTP_USUARIO
    msg["To"] = destino
    msg.set_content(
        f"Olá, {nome}!\n\n"
        f"Seu código para redefinir a senha é: {codigo}\n\n"
        f"Ele vale por {VALIDADE_CODIGO_MIN} minutos. "
        "Se não foi você quem pediu, é só ignorar este e-mail.\n"
    )
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as servidor:
            servidor.starttls()
            servidor.login(SMTP_USUARIO, SMTP_SENHA)
            servidor.send_message(msg)
    except Exception as e:
        print(f"[ERRO AO ENVIAR E-MAIL] {e}")


@app.post("/api/esqueci-senha")
def esqueci_senha():
    email = (request.get_json() or {}).get("email", "").strip().lower()
    u = banco().execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
    if u:
        codigo = f"{secrets.randbelow(1_000_000):06d}"
        expira = (datetime.now() + timedelta(minutes=VALIDADE_CODIGO_MIN)).strftime(FORMATO_DATA)
        banco().execute(
            "INSERT OR REPLACE INTO codigos_reset (usuario_id, codigo_hash, expira_em, tentativas) "
            "VALUES (?, ?, ?, 0)",
            (u["id"], generate_password_hash(codigo), expira),
        )
        banco().commit()
        enviar_codigo_por_email(u["email"], u["nome"], codigo)
    # Mesma resposta exista o e-mail ou não, para ninguém descobrir quem tem conta
    return jsonify(mensagem=f"Se esse e-mail tiver cadastro, enviamos um código de 6 dígitos. Ele vale por {VALIDADE_CODIGO_MIN} minutos.")


@app.post("/api/redefinir-senha")
def redefinir_senha():
    d = request.get_json() or {}
    email = d.get("email", "").strip().lower()
    codigo = str(d.get("codigo", "")).strip()
    nova = d.get("nova_senha", "")
    if len(nova) < 6:
        return erro("A nova senha precisa ter pelo menos 6 caracteres.")

    invalido = "Código inválido ou expirado. Peça um novo código."
    u = banco().execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
    r = u and banco().execute("SELECT * FROM codigos_reset WHERE usuario_id = ?", (u["id"],)).fetchone()
    if not r:
        return erro(invalido)

    expirou = datetime.now() > datetime.strptime(r["expira_em"], FORMATO_DATA)
    if expirou or r["tentativas"] >= MAX_TENTATIVAS:
        banco().execute("DELETE FROM codigos_reset WHERE usuario_id = ?", (u["id"],))
        banco().commit()
        return erro(invalido)

    if not check_password_hash(r["codigo_hash"], codigo):
        banco().execute("UPDATE codigos_reset SET tentativas = tentativas + 1 WHERE usuario_id = ?", (u["id"],))
        banco().commit()
        return erro("Código incorreto.")

    banco().execute("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (generate_password_hash(nova), u["id"]))
    banco().execute("DELETE FROM codigos_reset WHERE usuario_id = ?", (u["id"],))
    banco().execute("DELETE FROM sessoes WHERE usuario_id = ?", (u["id"],))  # desloga de todos os aparelhos
    banco().commit()
    return jsonify(mensagem="Senha alterada! Entre com a nova senha.")


criar_tabelas()

if __name__ == "__main__":
    app.run(port=5000, debug=True)